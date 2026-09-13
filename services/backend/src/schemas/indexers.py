"""Schemas for the indexer endpoints."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import Field, field_serializer

from src.schemas.base import APIModel
from src.schemas.common import PaginatedResponse
from src.schemas.enums import IndexerEventType, IndexerHealth, IndexerLogLevel


def _as_utc_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


class Indexer(APIModel):
    id: int
    name: str
    health: IndexerHealth
    enabled: bool
    protocol: str | None = None
    privacy: str | None = None
    priority: int | None = None
    supports_search: bool = False
    supports_rss: bool = False
    indexer_urls: list[str] = Field(default_factory=list)
    disabled_till: datetime | None = None
    most_recent_failure: datetime | None = None
    initial_failure: datetime | None = None

    @field_serializer("disabled_till", "most_recent_failure", "initial_failure")
    def _serialize_datetime(self, value: datetime | None) -> str | None:
        return _as_utc_iso(value)


class IndexersResponse(APIModel):
    indexers: list[Indexer]


class IndexerTestResult(APIModel):
    indexer_id: int
    success: bool
    name: str | None = None
    errors: list[str] = Field(default_factory=list)


class IndexerTestResults(APIModel):
    results: list[IndexerTestResult]


class IndexerHistoryEntry(APIModel):
    id: int
    indexer_id: int
    occurred_at: datetime
    event_type: IndexerEventType
    successful: bool
    indexer_name: str | None = None
    query: str | None = None
    title: str | None = None
    source: str | None = None
    elapsed_ms: int | None = None
    data: dict[str, str] = Field(default_factory=dict)

    @field_serializer("occurred_at")
    def _serialize_occurred_at(self, value: datetime) -> str | None:
        return _as_utc_iso(value)


class IndexerHistoryResponse(PaginatedResponse):
    history: list[IndexerHistoryEntry]


class IndexerLogEntry(APIModel):
    id: int
    occurred_at: datetime
    level: IndexerLogLevel
    message: str
    component: str | None = None
    method: str | None = None
    exception: str | None = None
    exception_type: str | None = None

    @field_serializer("occurred_at")
    def _serialize_occurred_at(self, value: datetime) -> str | None:
        return _as_utc_iso(value)


class IndexerLogsResponse(PaginatedResponse):
    logs: list[IndexerLogEntry]


__all__ = [
    "Indexer",
    "IndexerHistoryEntry",
    "IndexerHistoryResponse",
    "IndexerLogEntry",
    "IndexerLogsResponse",
    "IndexerTestResult",
    "IndexerTestResults",
    "IndexersResponse",
]
