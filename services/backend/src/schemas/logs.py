"""Schemas for log retrieval endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from src.schemas.base import APIModel
from src.schemas.common import PaginatedResponse
from src.schemas.enums import RequestLogLevel


class RequestLogEntry(APIModel):
    id: str
    occurred_at: int = Field(serialization_alias="occurredAt")
    timestamp: str
    level: RequestLogLevel
    message: str
    source: str | None = None
    metadata: dict[str, Any] | None = None
    stack_trace: str | None = Field(default=None, serialization_alias="stackTrace")


class LogsResponse(PaginatedResponse):
    logs: list[RequestLogEntry]


__all__ = ["LogsResponse", "RequestLogEntry"]
