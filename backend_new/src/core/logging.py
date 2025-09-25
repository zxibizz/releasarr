"""Central logging configuration helpers using Loguru."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from loguru import logger

from src.settings.config import AppSettings


class InterceptHandler(logging.Handler):
    """Redirect standard logging records to Loguru."""

    def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover - thin adapter
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        logger.bind(logger_name=record.name).opt(exception=record.exc_info).log(
            level,
            record.getMessage(),
        )


def configure_logging(settings: AppSettings) -> None:
    """Configure Loguru sinks for console and file output."""

    logger.remove()
    logger.configure(extra={"request_id": None})

    level = settings.log_level.upper()

    logger.add(
        sys.stdout,
        level=level,
        enqueue=True,
        serialize=settings.log_json,
        backtrace=False,
        diagnose=False,
    )

    log_path = Path(settings.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger.add(
        log_path,
        level=level,
        enqueue=True,
        serialize=True,
        rotation="10 MB",
        retention="14 days",
        backtrace=False,
        diagnose=False,
    )

    logging.basicConfig(
        handlers=[InterceptHandler()],
        level=getattr(logging, level, logging.INFO),
        force=True,
    )


def get_logger(**extra: object):
    """Return a Loguru logger bound with optional context."""

    return logger.bind(**extra)


__all__ = ["configure_logging", "get_logger", "logger"]
