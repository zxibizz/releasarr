"""Schemas for the indexer endpoints."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import Field, field_serializer

from src.schemas.base import APIModel
from src.schemas.enums import IndexerHealth


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


__all__ = [
    "Indexer",
    "IndexerTestResult",
    "IndexerTestResults",
    "IndexersResponse",
]
