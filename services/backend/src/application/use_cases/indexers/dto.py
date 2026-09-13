"""Data transfer objects returned by indexer use cases."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime

from src.domain.enums import IndexerEventType, IndexerHealth, IndexerLogLevel


@dataclass(slots=True)
class IndexerDTO:
    """An indexer together with the health derived from its failure history."""

    indexer_id: int
    name: str
    health: IndexerHealth
    enabled: bool
    protocol: str | None
    privacy: str | None
    priority: int | None
    supports_search: bool
    supports_rss: bool
    indexer_urls: tuple[str, ...]
    disabled_till: datetime | None
    most_recent_failure: datetime | None
    initial_failure: datetime | None


@dataclass(slots=True)
class IndexerTestResultDTO:
    indexer_id: int
    success: bool
    name: str | None = None
    errors: tuple[str, ...] = field(default_factory=tuple)


@dataclass(slots=True)
class IndexerEventDTO:
    """One entry from Prowlarr's indexer history."""

    event_id: int
    indexer_id: int
    occurred_at: datetime
    event_type: IndexerEventType
    successful: bool
    indexer_name: str | None
    query: str | None
    title: str | None
    source: str | None
    elapsed_ms: int | None
    data: Mapping[str, str]


@dataclass(slots=True)
class IndexerHistoryPageDTO:
    events: tuple[IndexerEventDTO, ...]
    total: int
    page: int
    per_page: int


@dataclass(slots=True)
class IndexerLogDTO:
    """One line from the search provider's own log."""

    log_id: int
    occurred_at: datetime
    level: IndexerLogLevel
    message: str
    component: str | None
    method: str | None
    exception: str | None
    exception_type: str | None


@dataclass(slots=True)
class IndexerLogsPageDTO:
    logs: tuple[IndexerLogDTO, ...]
    total: int
    page: int
    per_page: int


__all__ = [
    "IndexerDTO",
    "IndexerEventDTO",
    "IndexerHistoryPageDTO",
    "IndexerLogDTO",
    "IndexerLogsPageDTO",
    "IndexerTestResultDTO",
]
