"""
Health check endpoints for liveness and readiness probes.

GET /health        — Liveness: confirms the web process is alive.
GET /health/ready  — Readiness: validates PostgreSQL and Redis connectivity.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text
from app.database.session import async_session_factory
from app.core.logging import logger

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Liveness probe")
async def health_liveness() -> JSONResponse:
    """
    Returns HTTP 200 immediately.
    Used by Docker healthcheck and load balancer to confirm the process is alive.
    """
    return JSONResponse(content={"status": "ok", "service": "AntiGraffiti AI"})


@router.get("/health/ready", summary="Readiness probe")
async def health_readiness() -> JSONResponse:
    """
    Checks active connections to PostgreSQL and Redis.
    Returns HTTP 200 if all dependencies are reachable, HTTP 503 otherwise.
    """
    checks: dict = {}
    healthy = True

    # Check PostgreSQL
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as exc:
        logger.error("PostgreSQL readiness check failed: %s", exc)
        checks["postgres"] = f"error: {exc}"
        healthy = False

    # Check Redis
    try:
        import redis.asyncio as aioredis
        from app.config import get_settings
        settings = get_settings()
        r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        await r.ping()
        await r.aclose()
        checks["redis"] = "ok"
    except Exception as exc:
        logger.error("Redis readiness check failed: %s", exc)
        checks["redis"] = f"error: {exc}"
        healthy = False

    status_code = 200 if healthy else 503
    return JSONResponse(
        content={"status": "ready" if healthy else "degraded", "checks": checks},
        status_code=status_code,
    )
