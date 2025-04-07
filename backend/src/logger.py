from __future__ import annotations

import inspect
import logging
import sys

import loguru
from loguru import logger as base_logger

from src.settings import app_settings


class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        # Get corresponding Loguru level if it exists.
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message.
        frame, depth = inspect.currentframe(), 0
        while frame:
            filename = frame.f_code.co_filename
            is_logging = filename == logging.__file__
            is_frozen = "importlib" in filename and "_bootstrap" in filename
            if depth > 0 and not (is_logging or is_frozen):
                break
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def _init_logger() -> loguru.Logger:
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    base_logger.remove()

    logger = base_logger.bind()
    logger.add(
        sys.stderr,
        format="{time} | <lvl>{level}</lvl> | {name} | {message}",
        level="INFO",
        colorize=True,
    )
    logger.add(
        app_settings.LOG_FILE,
        format="{message}",
        level="INFO",
        rotation="100 MB",
        retention="10 days",
        filter=lambda record: "component" in record["extra"],
        serialize=True,
    )
    return logger


logger = _init_logger()
