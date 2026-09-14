"""Central logging configuration helpers using Loguru."""

from __future__ import annotations

import inspect
import logging
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

from src.domain.enums import LogService
from src.settings.config import AppSettings

if TYPE_CHECKING:
    from loguru import Logger
else:
    Logger = logger.__class__

if TYPE_CHECKING:
    from loguru import Record

# Credentials that upstream libraries put in the query string of a logged URL.
_SECRET_QUERY_PARAMS = re.compile(
    r"((?:api_?key|apikey|token|password)=)[^&\s\"']+",
    re.IGNORECASE,
)

# httpx logs every outbound request URL at INFO, which is both the bulk of our log
# volume and the one place a credential reaches the log file. Metadata providers
# that take their key as a query parameter would otherwise leak it.
_MUTED_LIBRARIES = ("httpx", "httpcore")


def redact_secrets(record: Record) -> None:
    """Mask credentials in a record's message before any sink receives it.

    The log file is served to the browser by the /logs endpoint, so a key that
    reaches a record is a key on screen. Patching here covers every sink and the
    serialized ``text`` field along with it.
    """
    record["message"] = _SECRET_QUERY_PARAMS.sub(r"\1***", record["message"])


class InterceptHandler(logging.Handler):
    """Redirect standard logging records to Loguru."""

    def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover - thin adapter
        level: int | str
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Without this, every intercepted record is attributed to this handler
        # rather than to the library that logged it, and the /logs endpoint
        # reports the source of all of them as src.core.logging.
        frame, depth = inspect.currentframe(), 0
        while frame and (depth == 0 or frame.f_code.co_filename == logging.__file__):
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def _resolve_level(name: str) -> str:
    """Return a level Loguru recognises, falling back to ``INFO``.

    An unusable setting must not take the whole process down on startup, since
    logging is configured before anything else can report the problem.
    """
    try:
        logger.level(name)
    except ValueError:
        return "INFO"
    return name


def _file_level(level: str) -> str:
    """Return the level the log file records at, never quieter than ``INFO``.

    The file is what a request's activity view is built from, so raising the
    console threshold must not blank that view. A more verbose setting still
    applies, since an operator asking for debug output wants it on disk too.
    """
    return level if logger.level(level).no < logger.level("INFO").no else "INFO"


def _log_path(settings: AppSettings, service: LogService) -> Path:
    """Return the file the process being configured writes.

    Each process owns one, so a rotation in either can no longer move the other's
    records into a sibling the other is not writing to.
    """

    if service is LogService.SCHEDULER:
        return Path(settings.scheduler_log_file)
    return Path(settings.log_file)


def configure_logging(settings: AppSettings, *, service: LogService) -> None:
    """Configure Loguru sinks for console and file output.

    ``service`` names the process being configured. It is bound as a default
    extra, so every record this process writes can be told apart from the other
    process's records, and it selects the file this process writes to.
    """

    logger.remove()
    logger.configure(extra={"request_id": None, "service": service.value}, patcher=redact_secrets)

    level = _resolve_level(settings.log_level.upper())

    logger.add(
        sys.stdout,
        level=level,
        enqueue=True,
        serialize=settings.log_json,
        backtrace=False,
        diagnose=False,
    )

    log_path = _log_path(settings, service)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger.add(
        log_path,
        level=_file_level(level),
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

    for name in _MUTED_LIBRARIES:
        logging.getLogger(name).setLevel(logging.WARNING)


def get_logger(**extra: object) -> Logger:
    """Return a Loguru logger bound with optional context."""

    return logger.bind(**extra)


__all__ = ["configure_logging", "get_logger", "logger"]
