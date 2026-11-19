"""
aiogram 3.x Bot and Dispatcher configuration.

Creates the Bot instance, configures FSM storage (Redis),
registers all routers and middlewares.
"""

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage

from app.bot.handlers import common, report, user_reports
from app.bot.middlewares.error_handler import ErrorHandlerMiddleware
from app.bot.middlewares.throttling import ThrottlingMiddleware
from app.bot.middlewares.user_sync import UserSyncMiddleware
from app.config import get_settings
from app.core.logging import logger

settings = get_settings()


def create_bot() -> Bot:
    """Creates and returns a configured aiogram Bot instance."""
    return Bot(
        token=settings.TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher(redis_url: str) -> Dispatcher:
    """
    Creates an aiogram Dispatcher with:
      - Redis FSM storage (persistent across restarts)
      - UserSyncMiddleware (auto-register Telegram users in DB)
      - ThrottlingMiddleware (rate limiting via Redis Token Bucket)
      - ErrorHandlerMiddleware (global exception boundary)
      - All feature routers included
    """
    storage = RedisStorage.from_url(redis_url)
    dp = Dispatcher(storage=storage)

    # Register middlewares in order of execution
    dp.update.outer_middleware(ErrorHandlerMiddleware())
    dp.message.middleware(UserSyncMiddleware())
    dp.callback_query.middleware(UserSyncMiddleware())
    dp.message.middleware(ThrottlingMiddleware(redis_url))

    # Include feature routers
    dp.include_router(common.router)
    dp.include_router(report.router)
    dp.include_router(user_reports.router)

    logger.info("aiogram Dispatcher configured with %d routers.", 3)
    return dp
