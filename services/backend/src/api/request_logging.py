"""Access logging for the API process.

The API server has access logging of its own, but it is useless to the logs view:
uvicorn configures its loggers with ``propagate: false``, so nothing it writes
reaches Loguru or the file the /logs endpoint reads. These requests are logged
here instead, through the same structured sink as everything else, which also
means they arrive with status and duration attached rather than as a formatted
line to be parsed back apart.

They are logged at DEBUG: one line per request is chatter the UI itself produces
several times a minute through its own polling, so the file - whose floor is
INFO - stays readable unless the configured level asks for them.
"""

from __future__ import annotations

import time

from fastapi import FastAPI, Request, Response

from src.core.container import get_container
from src.core.logging import get_logger
from src.domain.enums import LogComponent

__all__ = ["register_request_logging"]

_http_logger = get_logger(LogComponent.API_HTTP)
_auth_logger = get_logger(LogComponent.API_AUTH)


def register_request_logging(app: FastAPI) -> None:
    """Log one line per request served, once the response is known."""

    @app.middleware("http")
    async def log_request(request: Request, call_next) -> Response:
        started = time.perf_counter()
        # Assumed until the handler returns one: an exception that escapes the
        # exception handlers still leaves Starlette answering 500, and a request
        # that never appears in the log is worse than one attributed roughly.
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            # The path only. A query string can carry a credential, the redaction
            # patcher only rewrites the message, and this file is served to the
            # browser by /logs -- so a key passed into metadata would be a key on
            # screen.
            path = request.url.path
            log = _auth_logger if path.startswith("/auth") else _http_logger
            log.debug(
                f"{request.method} {path}",
                status_code=status_code,
                duration_ms=round((time.perf_counter() - started) * 1000),
            )
            # A change another process wrote shows up here without a restart. It
            # is one rate-limited revision read, and failures must not 500 a
            # request that already succeeded.
            try:
                await get_container().apply_settings_updates()
            except Exception:
                _http_logger.exception("Failed to refresh settings")
