"""Ports for inspecting and exercising the configured search indexers."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol


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


class IndexerDirectory(Protocol):
    """Read and test the indexers a search provider is configured with."""

    async def list_indexers(self) -> Sequence[IndexerRecord]:
        """Return every known indexer, including the ones switched off."""

    async def test_indexer(self, indexer_id: int) -> IndexerTestResultRecord:
        """Exercise a single indexer, clearing its failure back-off when it passes.

        Raises :class:`IndexerNotFoundError` when the identifier is unknown.
        """

    async def test_all_indexers(self) -> Sequence[IndexerTestResultRecord]:
        """Exercise every enabled indexer in one call."""


__all__ = [
    "IndexerDirectory",
    "IndexerNotFoundError",
    "IndexerRecord",
    "IndexerTestResultRecord",
]
