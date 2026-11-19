"""
FastAPI application entry point with lifespan management.

Lifespan handles:
  - PostgreSQL async engine pool initialization
  - Redis connection validation
  - aiogram Bot + Dispatcher startup and webhook registration
  - Super admin auto-provisioning on first run
  - Graceful shutdown of all resources

No Long Polling is used. The bot runs exclusively via Telegram Webhook.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.health import router as health_router
from app.api.webhook import router as webhook_router
from app.bot.dispatcher import create_bot, create_dispatcher
from app.config import get_settings
from app.core.logging import logger, setup_logging
from app.core.security import hash_password
from app.database.models.admin import Admin
from app.database.models.enums import AdminRole
from app.database.session import async_session_factory, close_db
from sqlalchemy import select

settings = get_settings()


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Manages application startup and shutdown lifecycle.
    All heavy initialization happens here, not at module import time.
    """
    setup_logging(debug=settings.APP_DEBUG)
    logger.info("Starting %s (env=%s)", settings.APP_NAME, settings.APP_ENV)

    # ── 1. Validate Redis connectivity ────────────────────────────────────────
    try:
        r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=5)
        await r.ping()
        await r.aclose()
        logger.info("Redis connection: OK (%s)", settings.REDIS_URL.split("@")[-1])
    except Exception as exc:
        logger.critical("Cannot connect to Redis: %s — aborting startup.", exc)
        raise

    # ── 2. Initialize aiogram Bot + Dispatcher ────────────────────────────────
    bot = create_bot()
    dp = create_dispatcher(settings.REDIS_URL)

    # Expose bot and dispatcher to webhook handler via app.state
    app.state.bot = bot
    app.state.dispatcher = dp

    # ── 3. Auto-provision super admin on first run ────────────────────────────
    await _provision_super_admin()

    # ── 4. Register Telegram Webhook ──────────────────────────────────────────
    await _register_webhook(bot)

    logger.info("%s startup complete — ready to accept Telegram updates.", settings.APP_NAME)

    yield  # Application is running

    # ── Shutdown: close all resources ─────────────────────────────────────────
    logger.info("Shutting down %s...", settings.APP_NAME)
    await bot.session.close()
    await close_db()
    logger.info("Shutdown complete.")


# ── FastAPI Application Factory ───────────────────────────────────────────────

def create_app() -> FastAPI:
    """Creates and configures the FastAPI application instance."""

    _app = FastAPI(
        title=settings.APP_NAME,
        description="AntiGraffiti AI — Urban Graffiti Detection Platform",
        version="1.0.0",
        docs_url="/docs" if settings.APP_DEBUG else None,  # Hide Swagger in production
        redoc_url="/redoc" if settings.APP_DEBUG else None,
        lifespan=lifespan,
    )

    # ── CORS Middleware ───────────────────────────────────────────────────────
    _app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_hosts_list,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    # ── Routers ───────────────────────────────────────────────────────────────
    _app.include_router(health_router)
    _app.include_router(webhook_router)

    # Admin panel router (registered separately to allow template mounts)
    from app.admin.routes import router as admin_router
    _app.include_router(admin_router, prefix="/admin")

    # Static files for admin panel CSS/JS
    try:
        _app.mount(
            "/static",
            StaticFiles(directory="app/admin/static"),
            name="static",
        )
    except Exception:
        logger.warning("Static files directory not found — skipping mount.")

    logger.info("FastAPI application created with %d routes.", len(_app.routes))
    return _app


# ── Helper: Register Telegram Webhook ────────────────────────────────────────

async def _register_webhook(bot) -> None:
    """
    Registers the HTTPS Webhook URL with Telegram Bot API.
    Uses the WEBHOOK_SECRET to authenticate incoming updates.
    """
    webhook_url = settings.full_webhook_url
    try:
        await bot.set_webhook(
            url=webhook_url,
            secret_token=settings.WEBHOOK_SECRET,
            allowed_updates=["message", "callback_query", "inline_query"],
            drop_pending_updates=True,
        )
        logger.info("Telegram Webhook registered: %s", webhook_url)
    except Exception as exc:
        logger.error("Failed to register Telegram Webhook: %s", exc)
        # Non-fatal in dev mode; fatal in production would prevent bot from working


# ── Helper: Provision Super Admin ────────────────────────────────────────────

async def _provision_super_admin() -> None:
    """Creates the initial SUPER_ADMIN account if no admins exist."""
    try:
        async with async_session_factory() as session:
            result = await session.execute(select(Admin).limit(1))
            existing = result.scalar_one_or_none()

            if existing:
                return  # Admins already exist — skip provisioning

            admin = Admin(
                username=settings.ADMIN_USERNAME,
                password_hash=hash_password(settings.ADMIN_PASSWORD),
                role=AdminRole.SUPER_ADMIN,
                is_active=True,
            )
            session.add(admin)
            await session.commit()
            logger.info(
                "Super admin '%s' provisioned automatically on first startup.",
                settings.ADMIN_USERNAME,
            )
    except Exception as exc:
        logger.error("Super admin provisioning failed: %s", exc)


# ── Application instance ──────────────────────────────────────────────────────

app = create_app()
