"""Access logging for the API process.

The API server has access logging of its own, but it is useless to the logs view:
uvicorn configures its loggers with ``propagate: false``, so nothing it writes
reaches Loguru or the file the /logs endpoint reads. These requests are logged
here instead, through the same structured sink as everything else, which also
means they arrive with status and duration attached rather than as a formatted
line to be parsed back apart.
"""

from __future__ import annotations

import time

from fastapi import FastAPI, Request, Response

from src.core.logging import get_logger
from src.domain.enums import LogComponent

__all__ = ["register_request_logging"]

_logger = get_logger(LogComponent.API_HTTP)


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
            _logger.info(
                f"{request.method} {request.url.path}",
                status_code=status_code,
                duration_ms=round((time.perf_counter() - started) * 1000),
            )
