"""Central logging configuration helpers."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from logging.config import dictConfig

from src.settings.config import AppSettings


def _build_logging_config(settings: AppSettings) -> Mapping[str, object]:
    level = settings.log_level.upper()

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            },
            "json": {
                "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "fmt": "%(asctime)s %(levelname)s %(name)s %(message)s",
            },
        },
        "handlers": {
            "default": {
                "class": "logging.StreamHandler",
                "level": level,
                "formatter": "json" if settings.log_json else "standard",
            },
        },
        "root": {
            "handlers": ["default"],
            "level": level,
        },
    }


def configure_logging(settings: AppSettings) -> None:
    """Configure the global logging module according to settings."""

    config = _build_logging_config(settings)
    dictConfig(config)  # type: ignore[arg-type]

    # Quiet overly chatty default loggers.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a module-level logger."""

    return logging.getLogger(name)


__all__ = ["configure_logging", "get_logger"]
