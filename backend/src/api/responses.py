"""Utilities for documenting standard API error responses."""

from __future__ import annotations

from typing import Any

from src.schemas.common import ErrorResponse

ResponsesDoc = dict[int | str, dict[str, Any]]


def error_response(description: str) -> dict[str, Any]:
    """Return a FastAPI response metadata entry for the common error schema."""

    return {"model": ErrorResponse, "description": description}


def error_responses(entries: dict[int, str]) -> ResponsesDoc:
    """Build an OpenAPI ``responses`` mapping from status code to description."""

    return {code: error_response(description) for code, description in entries.items()}


__all__ = ["ResponsesDoc", "error_response", "error_responses"]
