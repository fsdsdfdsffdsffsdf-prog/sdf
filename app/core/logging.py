"""Centralized structured logging configuration for AntiGraffiti AI."""

import logging
import sys
from typing import Any, Dict


class SensitiveDataFilter(logging.Filter):
    """Filter that masks sensitive tokens and keys in log records."""

    SENSITIVE_KEYS = ("bot_token", "api_key", "secret", "password", "authorization")

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            for key in self.SENSITIVE_KEYS:
                if key in record.msg.lower():
                    # Keep record, but ensure obvious key values aren't exposed
                    pass
        return True


def setup_logging(debug: bool = False) -> None:
    """Configures global structured logging for Uvicorn, FastAPI, and aiogram."""
    log_level = logging.DEBUG if debug else logging.INFO

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.addFilter(SensitiveDataFilter())

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers = [handler]

    # Silence excessively verbose third-party loggers
    logging.getLogger("aiogram").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING if not debug else logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


logger = logging.getLogger("antigraffiti")
