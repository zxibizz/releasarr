"""Common error helpers and handlers for the API layer.

Domain exceptions are translated into the canonical error response shape by a
single registry of handlers (see :data:`DOMAIN_ERROR_MAP` and
:func:`register_exception_handlers`), so individual routes no longer need to
wrap use-case calls in repetitive ``try``/``except`` blocks.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.application.use_cases.releases.exceptions import (
    ReleaseActionNotAllowedError,
    ReleaseConflictError,
    ReleaseDownloadConflictError,
    ReleaseDownloadFailedError,
    ReleaseFileNotFoundError,
    ReleaseNotFoundError,
)
from src.application.use_cases.requests.exceptions import (
    EmptyUpdatePayloadError,
    MediaRequestNotFoundError,
)

ErrorDetail = Mapping[str, Any] | Sequence[Any] | None
Handler = Callable[[Request, Exception], Awaitable[JSONResponse]]

# Maps a domain exception type to the (status code, error code) it should emit.
DOMAIN_ERROR_MAP: dict[type[Exception], tuple[int, str]] = {
    MediaRequestNotFoundError: (status.HTTP_404_NOT_FOUND, "request_not_found"),
    EmptyUpdatePayloadError: (status.HTTP_400_BAD_REQUEST, "empty_update"),
    ReleaseNotFoundError: (status.HTTP_404_NOT_FOUND, "release_not_found"),
    ReleaseFileNotFoundError: (status.HTTP_404_NOT_FOUND, "release_file_not_found"),
    ReleaseActionNotAllowedError: (status.HTTP_409_CONFLICT, "release_action_conflict"),
    ReleaseConflictError: (status.HTTP_409_CONFLICT, "release_conflict"),
    ReleaseDownloadConflictError: (status.HTTP_409_CONFLICT, "release_download_conflict"),
    ReleaseDownloadFailedError: (status.HTTP_500_INTERNAL_SERVER_ERROR, "release_download_failed"),
}


def _error_payload(code: str, message: str, details: ErrorDetail = None) -> dict[str, Any]:
    return {"code": code, "message": message, "details": details}


def api_error(
    status_code: int,
    code: str,
    message: str,
    details: ErrorDetail = None,
) -> HTTPException:
    """Raiseable HTTP exception producing a spec-compliant error body."""

    payload = _error_payload(code, message, details)
    return HTTPException(status_code=status_code, detail=payload)


def _domain_handler(status_code: int, code: str) -> Handler:
    async def handler(request: Request, exc: Exception) -> JSONResponse:
        payload = _error_payload(code, str(exc))
        return JSONResponse(status_code=status_code, content=payload)

    return handler


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Translate FastAPI validation errors into the standardized response body."""

    errors = exc.errors() if isinstance(exc, RequestValidationError) else []
    detail = _error_payload("validation_error", "Request validation failed", errors)
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, content=detail)


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Ensure HTTP exceptions emit the canonical error response shape."""

    status_code = exc.status_code if isinstance(exc, HTTPException) else 500
    detail = exc.detail if isinstance(exc, HTTPException) else None
    if isinstance(detail, dict) and {"code", "message"}.issubset(detail.keys()):
        payload = _error_payload(detail["code"], detail["message"], detail.get("details"))
    else:
        message = detail if isinstance(detail, str) else str(detail or status_code)
        payload = _error_payload("http_error", message)
    return JSONResponse(status_code=status_code, content=payload)


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Fallback handler for unexpected errors."""

    payload = _error_payload("internal_error", "An unexpected error occurred")
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=payload)


def register_exception_handlers(app: FastAPI) -> None:
    """Register validation, domain, and fallback exception handlers on ``app``."""

    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    for exc_type, (status_code, code) in DOMAIN_ERROR_MAP.items():
        app.add_exception_handler(exc_type, _domain_handler(status_code, code))
    app.add_exception_handler(Exception, unhandled_exception_handler)


__all__ = [
    "DOMAIN_ERROR_MAP",
    "api_error",
    "http_exception_handler",
    "register_exception_handlers",
    "unhandled_exception_handler",
    "validation_exception_handler",
]
