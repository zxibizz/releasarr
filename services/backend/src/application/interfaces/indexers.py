"""Ports for inspecting and exercising the configured search indexers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from src.domain.enums import IndexerEventType, IndexerLogLevel


class IndexerNotFoundError(LookupError):
    """Raised when the provider has no indexer under the requested identifier."""


@dataclass(slots=True)
class IndexerRecord:
    """One indexer as the search provider reports it.

    The failure timestamps are only populated while the provider is holding a
    grudge: it forgets them as soon as a query succeeds, so their absence means
    healthy rather than never-used.
    """

    indexer_id: int
    name: str
    enabled: bool
    protocol: str | None = None
    privacy: str | None = None
    priority: int | None = None
    supports_search: bool = False
    supports_rss: bool = False
    indexer_urls: tuple[str, ...] = ()
    disabled_till: datetime | None = None
    most_recent_failure: datetime | None = None
    initial_failure: datetime | None = None


@dataclass(slots=True)
class IndexerTestResultRecord:
    indexer_id: int
    success: bool
    name: str | None = None
    errors: tuple[str, ...] = field(default_factory=tuple)


@dataclass(slots=True)
class IndexerEventRecord:
    """One thing a provider recorded an indexer doing.

    The named fields are the handful worth showing in a column; ``data`` keeps
    whatever else the provider attached, which varies by event type and by
    indexer implementation.
    """

    event_id: int
    indexer_id: int
    occurred_at: datetime
    event_type: IndexerEventType
    successful: bool
    indexer_name: str | None = None
    query: str | None = None
    title: str | None = None
    source: str | None = None
    elapsed_ms: int | None = None
    data: Mapping[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class IndexerEventPage:
    """A page of indexer events, with the total the provider counted."""

    events: tuple[IndexerEventRecord, ...]
    total: int


@dataclass(slots=True)
class IndexerLogRecord:
    """One line from a search provider's own application log."""

    log_id: int
    occurred_at: datetime
    level: IndexerLogLevel
    message: str
    component: str | None = None
    method: str | None = None
    exception: str | None = None
    exception_type: str | None = None


@dataclass(slots=True)
class IndexerLogPage:
    """A page of provider log entries, with the total the provider counted."""

    logs: tuple[IndexerLogRecord, ...]
    total: int


class IndexerDirectory(Protocol):
    """Read and test the indexers a search provider is configured with.

    An implementation is always injected, even where no provider backs it:
    ``is_configured`` is how a caller tells the two apart, so nothing has to be
    absent from the type.
    """

    @property
    def is_configured(self) -> bool:
        """Whether a provider backs this directory and can be reached."""

    async def test_connection(self) -> None:
        """Verify the configured URL and key reach the provider, raising on failure."""

    async def list_indexers(self) -> Sequence[IndexerRecord]:
        """Return every known indexer, including the ones switched off."""

    async def list_history(
        self,
        *,
        page: int,
        per_page: int,
        indexer_id: int | None = None,
        event_type: IndexerEventType | None = None,
    ) -> IndexerEventPage:
        """Return one page of indexer events, newest first."""

    async def list_logs(
        self,
        *,
        page: int,
        per_page: int,
        min_level: IndexerLogLevel | None = None,
    ) -> IndexerLogPage:
        """Return one page of the provider's own log, newest first.

        ``min_level`` is a threshold: asking for warnings includes errors.
        """

    async def test_indexer(self, indexer_id: int) -> IndexerTestResultRecord:
        """Exercise a single indexer, clearing its failure back-off when it passes.

        Raises :class:`IndexerNotFoundError` when the identifier is unknown.
        """

    async def test_all_indexers(self) -> Sequence[IndexerTestResultRecord]:
        """Exercise every enabled indexer in one call."""


__all__ = [
    "IndexerDirectory",
    "IndexerEventPage",
    "IndexerEventRecord",
    "IndexerLogPage",
    "IndexerLogRecord",
    "IndexerNotFoundError",
    "IndexerRecord",
    "IndexerTestResultRecord",
]
