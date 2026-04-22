"""Common error helpers and handlers for the API layer."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

ErrorDetail = Mapping[str, Any] | None


def api_error(status_code: int, code: str, message: str, details: ErrorDetail = None) -> HTTPException:
    """Raiseable HTTP exception producing a spec-compliant error body."""

    payload = {"code": code, "message": message, "details": details}
    return HTTPException(status_code=status_code, detail=payload)


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Translate FastAPI validation errors into the standardized response body."""

    detail = {
        "code": "validation_error",
        "message": "Request validation failed",
        "details": exc.errors(),
    }
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=detail)


__all__ = ["api_error", "validation_exception_handler"]
