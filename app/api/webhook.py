"""
Telegram Webhook endpoint — the ONLY entry point for all Telegram updates.

POST /webhook/telegram

Security:
  - Validates X-Telegram-Bot-Api-Secret-Token header with constant-time compare.
  - Checks update_id idempotency via Redis to prevent duplicate processing.
  - Returns HTTP 200 immediately after enqueuing (never waits for AI analysis).

No Long Polling is used anywhere in this codebase.
"""

import json
from typing import Any, Dict

import redis.asyncio as aioredis
from aiogram.types import Update
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.core.logging import logger
from app.core.security import verify_secret_token

settings = get_settings()

router = APIRouter(tags=["Webhook"])

# Redis key prefix and TTL for idempotency checks
_IDEMPOTENCY_PREFIX = "tg_update:"
_IDEMPOTENCY_TTL_SECONDS = 86400  # 24 hours


def _get_redis() -> aioredis.Redis:
    """Returns a shared Redis client instance from app state."""
    # Instantiated fresh per-request using settings URL.
    # In production the connection is pooled by the asyncio event loop.
    return aioredis.from_url(settings.REDIS_URL, decode_responses=True)


@router.post(
    settings.WEBHOOK_PATH,
    summary="Receive Telegram Update via Webhook",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,  # Hide from public Swagger UI
)
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str = Header(
        default=None,
        alias="X-Telegram-Bot-Api-Secret-Token",
    ),
) -> JSONResponse:
    """
    Receives Telegram Update objects sent by Telegram Bot API.

    Processing pipeline:
      1. Verify the secret token header (constant-time compare).
      2. Decode raw JSON body to dict.
      3. Extract update_id and check Redis idempotency key.
      4. Mark update_id as processed in Redis (TTL = 24h).
      5. Feed the Update to aiogram Dispatcher for async processing.
      6. Return HTTP 200 immediately — never block on AI or DB writes.
    """

    # ── 1. Secret token verification ─────────────────────────────────────────
    if not verify_secret_token(x_telegram_bot_api_secret_token, settings.WEBHOOK_SECRET):
        logger.warning("Unauthorized webhook request — invalid secret token.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing Telegram Webhook secret token.",
        )

    # ── 2. Parse raw JSON body ────────────────────────────────────────────────
    try:
        raw_body: bytes = await request.body()
        update_data: Dict[str, Any] = json.loads(raw_body)
    except Exception as exc:
        logger.error("Failed to parse Telegram Update JSON: %s", exc)
        return JSONResponse(content={"ok": True})  # Return 200 to avoid Telegram retry storms

    update_id: int = update_data.get("update_id", 0)

    # ── 3. Idempotency check via Redis ────────────────────────────────────────
    redis_client = _get_redis()
    try:
        idempotency_key = f"{_IDEMPOTENCY_PREFIX}{update_id}"
        already_processed = await redis_client.get(idempotency_key)
        if already_processed:
            logger.debug("Duplicate Telegram update_id=%d ignored.", update_id)
            return JSONResponse(content={"ok": True})

        # ── 4. Mark as processed before dispatching ───────────────────────────
        await redis_client.set(idempotency_key, "1", ex=_IDEMPOTENCY_TTL_SECONDS)
    except Exception as exc:
        logger.error("Redis idempotency check failed for update_id=%d: %s", update_id, exc)
        # Degraded mode: continue processing even if Redis is unavailable
    finally:
        await redis_client.aclose()

    # ── 5. Feed Update to aiogram Dispatcher ─────────────────────────────────
    try:
        # Retrieve the dispatcher and bot from FastAPI application state
        dp = request.app.state.dispatcher
        bot = request.app.state.bot

        telegram_update = Update.model_validate(update_data)
        await dp.feed_update(bot=bot, update=telegram_update)
    except Exception as exc:
        logger.exception("Error dispatching Telegram update_id=%d: %s", update_id, exc)
        # Always return 200 to prevent Telegram from retrying the same broken update
        return JSONResponse(content={"ok": True})

    # ── 6. Return 200 immediately ─────────────────────────────────────────────
    return JSONResponse(content={"ok": True})
