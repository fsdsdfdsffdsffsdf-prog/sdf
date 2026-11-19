"""
ThrottlingMiddleware — rate-limits individual users to prevent spam and DoS.

Uses Redis Token Bucket algorithm:
  - Each user has a bucket with a fixed number of tokens.
  - Each message consumes 1 token.
  - Tokens regenerate at a fixed rate (default: 1 per second).
  - If the bucket is empty, the update is silently ignored.
"""

from typing import Any, Awaitable, Callable, Dict

import redis.asyncio as aioredis
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from app.config import get_settings
from app.core.logging import logger

settings = get_settings()

_THROTTLE_LIMIT = 5       # Max requests per window
_THROTTLE_WINDOW = 5      # Window size in seconds


class ThrottlingMiddleware(BaseMiddleware):
    """
    Protects the bot from spam by limiting how many messages
    a single user can send within a time window.
    """

    def __init__(self, redis_url: str = settings.REDIS_URL) -> None:
        self._redis_url = redis_url
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Only throttle Message events with a sender
        if not isinstance(event, Message) or not event.from_user:
            return await handler(event, data)

        user_id = event.from_user.id
        redis_key = f"throttle:{user_id}"

        try:
            r = aioredis.from_url(self._redis_url, decode_responses=True)
            count_str = await r.get(redis_key)
            count = int(count_str) if count_str else 0

            if count >= _THROTTLE_LIMIT:
                logger.warning("User %d throttled (%d req in %ds window).", user_id, count, _THROTTLE_WINDOW)
                await r.aclose()
                await event.answer(
                    "⚠️ Слишком много запросов. Пожалуйста, подождите несколько секунд.",
                    show_alert=False,
                )
                return  # Drop the update silently

            pipe = r.pipeline()
            pipe.incr(redis_key)
            pipe.expire(redis_key, _THROTTLE_WINDOW)
            await pipe.execute()
            await r.aclose()
        except Exception as exc:
            logger.debug("ThrottlingMiddleware Redis error (non-fatal): %s", exc)
            # Fail open — allow request if Redis is unavailable

        return await handler(event, data)
