"""Common error helpers and handlers for the API layer."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

ErrorDetail = Mapping[str, Any] | None


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


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Translate FastAPI validation errors into the standardized response body."""

    detail = _error_payload("validation_error", "Request validation failed", exc.errors())
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=detail)


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Ensure HTTP exceptions emit the canonical error response shape."""

    detail = exc.detail
    if isinstance(detail, dict) and {"code", "message"}.issubset(detail.keys()):
        payload = _error_payload(detail["code"], detail["message"], detail.get("details"))
    else:
        message = detail if isinstance(detail, str) else str(detail or exc.status_code)
        payload = _error_payload("http_error", message)
    return JSONResponse(status_code=exc.status_code, content=payload)


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Fallback handler for unexpected errors."""

    payload = _error_payload("internal_error", "An unexpected error occurred")
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=payload)


__all__ = [
    "api_error",
    "http_exception_handler",
    "unhandled_exception_handler",
    "validation_exception_handler",
]
