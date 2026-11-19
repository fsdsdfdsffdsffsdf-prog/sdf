"""
UserSyncMiddleware — automatically registers or updates Telegram users in PostgreSQL.

Runs on every incoming Update before reaching any handler.
Injects the `db_user` object into handler data so handlers
can reference the current user without additional DB queries.
"""

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.database.models.user import User
from app.database.session import async_session_factory


class UserSyncMiddleware(BaseMiddleware):
    """
    Middleware that upserts Telegram user data into the `users` table
    on every incoming message, callback_query, or inline_query.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Extract Telegram user from various update types
        tg_user = None
        update: Update = data.get("update") or data.get("event_update")

        if hasattr(event, "from_user") and event.from_user:
            tg_user = event.from_user
        elif update:
            if update.message and update.message.from_user:
                tg_user = update.message.from_user
            elif update.callback_query and update.callback_query.from_user:
                tg_user = update.callback_query.from_user

        if tg_user is None or tg_user.is_bot:
            return await handler(event, data)

        try:
            async with async_session_factory() as session:
                db_user = await _upsert_user(session, tg_user)
                await session.commit()
                data["db_user"] = db_user
        except Exception as exc:
            logger.error("UserSyncMiddleware failed for tg_id=%s: %s", tg_user.id, exc)
            data["db_user"] = None

        return await handler(event, data)


async def _upsert_user(session: AsyncSession, tg_user: Any) -> User:
    """Creates a new User or updates an existing one from Telegram profile data."""
    result = await session.execute(
        select(User).where(User.telegram_id == tg_user.id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            telegram_id=tg_user.id,
            username=tg_user.username,
            first_name=tg_user.first_name or "",
            last_name=tg_user.last_name,
            language_code=getattr(tg_user, "language_code", "ru"),
            is_active=True,
        )
        session.add(user)
        logger.info("New user registered: tg_id=%d @%s", tg_user.id, tg_user.username)
    else:
        # Update mutable profile fields that may change
        user.username = tg_user.username
        user.first_name = tg_user.first_name or user.first_name
        user.last_name = tg_user.last_name
        user.is_active = True

    return user
