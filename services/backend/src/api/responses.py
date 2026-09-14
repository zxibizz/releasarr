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


# Shared with every route module: spread into a route's own status-to-description
# dict before calling error_responses(), e.g.
# ``error_responses({**ADMIN_REQUIRED_RESPONSES, 404: "..."})``.
AUTH_REQUIRED_RESPONSES: dict[int, str] = {401: "Authentication required."}
ADMIN_REQUIRED_RESPONSES: dict[int, str] = {
    401: "Authentication required.",
    403: "Administrator privileges are required.",
}


__all__ = [
    "ADMIN_REQUIRED_RESPONSES",
    "AUTH_REQUIRED_RESPONSES",
    "ResponsesDoc",
    "error_response",
    "error_responses",
]
