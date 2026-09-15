"""Search external providers for candidate releases."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime

from loguru._logger import Logger

from src.application.interfaces.indexers import IndexerDirectory, IndexerRecord
from src.application.interfaces.releases import (
    ReleaseSearchResultRecord,
    ReleaseSearchResults,
    ReleaseSearchService,
    ReleaseSearchUnavailableError,
)
from src.application.use_cases.indexers.list_indexers import derive_health
from src.application.use_cases.releases.commands import SearchReleaseSourcesCommand
from src.application.use_cases.releases.dto import (
    IndexerSearchFailureDTO,
    ReleaseSearchResponseDTO,
)
from src.application.use_cases.releases.mappers import search_results_to_dto
from src.core.logging import get_logger
from src.domain.enums import IndexerHealth

DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_RETRIES = 1
DEFAULT_CONCURRENCY = 5


class SearchReleaseSourcesUseCase:
    """Orchestrate release source searches, one indexer at a time.

    Prowlarr's own aggregate ``/search`` sweeps every indexer in a single call,
    so one unresponsive indexer stalls (and, with the shared HTTP client's own
    retries, re-stalls) the whole search. Querying indexers individually lets a
    dead one fail on its own schedule while the rest still answer, at the cost
    of an extra ``list_indexers()`` round trip per search. An indexer Prowlarr
    is already backing off is reported as failed without being queried at all,
    since Prowlarr will refuse it regardless.
    """

    def __init__(
        self,
        search_service: ReleaseSearchService,
        *,
        directory: IndexerDirectory | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        retries: int = DEFAULT_RETRIES,
        concurrency: int = DEFAULT_CONCURRENCY,
        logger: Logger | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._search_service = search_service
        self._directory = directory
        self._timeout_seconds = timeout_seconds
        self._retries = retries
        self._concurrency = concurrency
        self._logger = logger or get_logger(component="release_search")
        self._clock = clock or (lambda: datetime.now(UTC))

    async def execute(self, command: SearchReleaseSourcesCommand) -> ReleaseSearchResponseDTO:
        if self._directory is None:
            # No Prowlarr configured: the search service is the in-memory
            # stand-in, which has no per-indexer notion to fan out over.
            results = await self._search_service.search(
                command.query, request_id=command.request_id
            )
            return search_results_to_dto(results)

        candidates = [
            indexer
            for indexer in await self._directory.list_indexers()
            if indexer.enabled and indexer.supports_search
        ]
        if not candidates:
            empty = ReleaseSearchResults(results=[], query=command.query, total_results=0)
            return search_results_to_dto(empty)

        # Prowlarr's own back-off (BLOCKED) means it has already given up on an
        # indexer for a while; querying it anyway would just eat the timeout
        # budget on a request Prowlarr will refuse. DEGRADED indexers - past
        # failures but not currently backed off - are still worth trying.
        now = self._clock()
        blocked: list[IndexerSearchFailureDTO] = []
        queryable: list[IndexerRecord] = []
        for indexer in candidates:
            if derive_health(indexer, now) is IndexerHealth.BLOCKED:
                blocked.append(self._blocked_failure(indexer))
            else:
                queryable.append(indexer)

        semaphore = asyncio.Semaphore(self._concurrency)
        outcomes = await asyncio.gather(
            *(self._search_one(indexer, command, semaphore) for indexer in queryable)
        )

        merged: list[ReleaseSearchResultRecord] = []
        failures: list[IndexerSearchFailureDTO] = [*blocked]
        for outcome in outcomes:
            if isinstance(outcome, IndexerSearchFailureDTO):
                failures.append(outcome)
            else:
                merged.extend(outcome.results)

        # Each indexer's own results arrive pre-sorted; re-sort once merged so
        # the combined list is globally ordered rather than indexer-by-indexer.
        merged.sort(key=lambda result: (-(result.seeders or 0), result.release_name.lower()))
        combined = ReleaseSearchResults(
            results=merged, query=command.query, total_results=len(merged)
        )
        return search_results_to_dto(
            combined, failed_indexers=failures, searched_indexers=len(candidates)
        )

    def _blocked_failure(self, indexer: IndexerRecord) -> IndexerSearchFailureDTO:
        self._logger.info(
            "Skipping indexer blocked by Prowlarr",
            indexer_id=indexer.indexer_id,
            indexer=indexer.name,
            disabled_till=indexer.disabled_till,
        )
        return IndexerSearchFailureDTO(
            indexer_id=indexer.indexer_id,
            name=indexer.name,
            reason=f"blocked by Prowlarr until {indexer.disabled_till}",
        )

    async def _search_one(
        self,
        indexer: IndexerRecord,
        command: SearchReleaseSourcesCommand,
        semaphore: asyncio.Semaphore,
    ) -> ReleaseSearchResults | IndexerSearchFailureDTO:
        last_reason = "unknown error"
        async with semaphore:
            for _attempt in range(self._retries + 1):
                try:
                    return await asyncio.wait_for(
                        self._search_service.search(
                            command.query,
                            request_id=command.request_id,
                            indexer_id=indexer.indexer_id,
                        ),
                        timeout=self._timeout_seconds,
                    )
                except TimeoutError:
                    last_reason = f"timed out after {self._timeout_seconds}s"
                except ReleaseSearchUnavailableError as exc:
                    last_reason = str(exc)

        self._logger.warning(
            "Indexer search failed",
            indexer_id=indexer.indexer_id,
            indexer=indexer.name,
            reason=last_reason,
            attempts=self._retries + 1,
        )
        return IndexerSearchFailureDTO(
            indexer_id=indexer.indexer_id,
            name=indexer.name,
            reason=last_reason,
        )


__all__ = ["SearchReleaseSourcesUseCase"]
