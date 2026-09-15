"""List the configured indexers with their current health."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from src.application.interfaces.indexers import IndexerDirectory, IndexerRecord
from src.application.use_cases.indexers.dto import IndexerDTO
from src.application.use_cases.indexers.exceptions import ProwlarrNotConfiguredError
from src.core.logging import get_logger
from src.domain.enums import IndexerHealth

logger = get_logger(component="indexers")


def derive_health(record: IndexerRecord, now: datetime) -> IndexerHealth:
    """Classify an indexer from its enabled flag and failure history.

    Prowlarr reports two unrelated kinds of "off". A cleared enable flag is a
    deliberate choice that stays put, so it outranks everything else. Its own
    back-off after repeated failures expires on its own, and the failure
    timestamps outlive it: an indexer that has recovered but not yet been
    queried successfully still carries them, which is worth showing without
    claiming the indexer is unusable.
    """

    if not record.enabled:
        return IndexerHealth.DISABLED
    if record.disabled_till is not None and record.disabled_till > now:
        return IndexerHealth.BLOCKED
    if record.most_recent_failure is not None or record.initial_failure is not None:
        return IndexerHealth.DEGRADED
    return IndexerHealth.HEALTHY


class ListIndexersUseCase:
    def __init__(
        self,
        directory: IndexerDirectory,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._directory = directory
        self._clock = clock or (lambda: datetime.now(UTC))

    async def execute(self) -> list[IndexerDTO]:
        if not self._directory.is_configured:
            raise ProwlarrNotConfiguredError

        now = self._clock()
        records = await self._directory.list_indexers()
        indexers = [self._to_dto(record, now) for record in records]

        unhealthy = sum(
            1
            for indexer in indexers
            if indexer.health in (IndexerHealth.BLOCKED, IndexerHealth.DEGRADED)
        )
        logger.debug("Listed indexers", total=len(indexers), unhealthy=unhealthy)
        return indexers

    def _to_dto(self, record: IndexerRecord, now: datetime) -> IndexerDTO:
        return IndexerDTO(
            indexer_id=record.indexer_id,
            name=record.name,
            health=derive_health(record, now),
            enabled=record.enabled,
            protocol=record.protocol,
            privacy=record.privacy,
            priority=record.priority,
            supports_search=record.supports_search,
            supports_rss=record.supports_rss,
            indexer_urls=tuple(record.indexer_urls),
            disabled_till=record.disabled_till,
            most_recent_failure=record.most_recent_failure,
            initial_failure=record.initial_failure,
        )


__all__ = ["ListIndexersUseCase", "derive_health"]
