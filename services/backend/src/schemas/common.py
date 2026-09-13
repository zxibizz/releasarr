"""Common schema pieces shared across endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from src.schemas.base import APIModel


class ErrorResponse(APIModel):
    code: str = Field(description="Machine-readable error identifier")
    message: str = Field(description="Human-readable explanation")
    details: dict[str, Any] | None = Field(default=None, description="Optional error metadata")


class SuccessResponse(APIModel):
    success: bool = Field(default=True)


class PaginatedResponse(APIModel):
    page: int = Field(ge=1)
    per_page: int = Field(ge=1)
    total: int = Field(ge=0)


__all__ = ["ErrorResponse", "PaginatedResponse", "SuccessResponse"]
