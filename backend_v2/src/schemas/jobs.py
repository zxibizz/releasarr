"""Schemas for async job responses."""

from __future__ import annotations

from src.schemas.base import APIModel
from src.schemas.enums import AsyncJobStatus


class AsyncOperationResponse(APIModel):
    operation: str
    status: AsyncJobStatus
    operation_id: str | None = None
    location: str | None = None
    message: str | None = None
    resource_id: str | None = None
    details: dict[str, object] | None = None


__all__ = ["AsyncOperationResponse"]
