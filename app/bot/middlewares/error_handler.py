"""
ErrorHandlerMiddleware — global exception boundary for all aiogram handlers.

Catches unhandled exceptions, logs the full stack trace, and sends
a friendly Russian-language error message to the user.
Prevents the entire update from failing silently.
"""

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from app.core.logging import logger


class ErrorHandlerMiddleware(BaseMiddleware):
    """Wraps every handler in a try/except to prevent uncaught crashes."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        try:
            return await handler(event, data)
        except Exception as exc:
            logger.exception("Unhandled exception in bot handler: %s", exc)

            # Attempt to notify the user
            if isinstance(event, Message) and event.from_user:
                try:
                    await event.answer(
                        "⚠️ Произошла внутренняя ошибка. Пожалуйста, попробуйте позже или введите /cancel и начните заново.",
                        parse_mode=None,
                    )
                except Exception:
                    pass  # If even sending the error message fails, give up gracefully
