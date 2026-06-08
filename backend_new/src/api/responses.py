"""Utilities for documenting standard API error responses."""

from __future__ import annotations

from typing import Any

from src.schemas.common import ErrorResponse


def error_response(description: str) -> dict[str, Any]:
    """Return a FastAPI response metadata entry for the common error schema."""

    return {"model": ErrorResponse, "description": description}


__all__ = ["error_response"]
