"""Data transfer objects returned by indexer use cases."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from src.domain.enums import IndexerHealth


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


__all__ = ["IndexerDTO", "IndexerTestResultDTO"]
