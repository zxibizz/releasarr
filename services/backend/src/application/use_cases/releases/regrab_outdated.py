"""Use case for re-grabbing releases that have been updated on the indexer."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from src.application.interfaces.indexers import IndexerDirectory
from src.application.interfaces.releases import (
    ReleaseDownloadService,
    ReleaseRecord,
    ReleaseRepository,
    ReleaseSearchService,
)
from src.application.interfaces.request_warnings import RequestWarningRepository
from src.application.use_cases.releases.auto_mapping import ReleaseAutoMapper
from src.application.use_cases.releases.regrab import ReleaseRegrapper
from src.application.use_cases.requests.recompute_state import RecomputeRequestStateUseCase
from src.core.logging import get_logger
from src.domain.enums import LogComponent

if TYPE_CHECKING:
    from loguru import Logger

# A check costs the tracker a search, so a sweep works through its candidates in
# bounded batches rather than all of them at once. What a batch then takes is
# `batch_size * indexer_delay_seconds` per tracker in the worst case.
DEFAULT_BATCH_SIZE = 25
DEFAULT_INDEXER_DELAY_SECONDS = 2.0


@dataclass(slots=True)
class RegrabResult:
    """What one sweep did, for the task summary in the queue view."""

    checked: int = 0
    regrabbed: int = 0
    failed: int = 0
    skipped: bool = False


class RegrabOutdatedReleasesUseCase:
    """Check candidate releases for updates (e.g. repacks) and re-download them.

    This is the sweep; the check on a single release lives in `ReleaseRegrapper`,
    which the on-demand refresh on a request drives as well.

    Trackers throttle a client that asks for too much at once, so the sweep is
    paced rather than exhaustive: it takes the least recently checked releases
    first, checks at most `batch_size` of them in a run, and leaves a gap between
    two checks against the same indexer. The backlog drains over successive runs,
    and the ordering is what makes that fair - each run picks up where the last
    one stopped instead of re-checking the same head of the list.
    """

    def __init__(
        self,
        repository: ReleaseRepository,
        search_service: ReleaseSearchService,
        download_service: ReleaseDownloadService,
        auto_mapper: ReleaseAutoMapper,
        warning_repository: RequestWarningRepository,
        recompute_state: RecomputeRequestStateUseCase,
        directory: IndexerDirectory,
        logger: Logger | None = None,
        clock: Callable[[], datetime] | None = None,
        batch_size: int = DEFAULT_BATCH_SIZE,
        indexer_delay_seconds: float = DEFAULT_INDEXER_DELAY_SECONDS,
        sleeper: Callable[[float], Awaitable[None]] | None = None,
    ) -> None:
        self._repository = repository
        self._search_service = search_service
        self._download_service = download_service
        self._logger = logger or get_logger(LogComponent.USECASE_REGRAB_OUTDATED)
        self._clock = clock or (lambda: datetime.now(UTC))
        self._batch_size = max(1, batch_size)
        self._indexer_delay_seconds = max(0.0, indexer_delay_seconds)
        self._sleep = sleeper or asyncio.sleep
        self._regrapper = ReleaseRegrapper(
            repository=repository,
            search_service=search_service,
            download_service=download_service,
            auto_mapper=auto_mapper,
            warning_repository=warning_repository,
            recompute_state=recompute_state,
            directory=directory,
            logger=self._logger,
            clock=self._clock,
        )

    async def execute(self) -> RegrabResult:
        """Process one batch of potential outdated releases."""
        if not self._search_service.is_configured or not self._download_service.is_configured:
            # A re-grab is a search plus a download, so there is nothing to check
            # and nothing to reach for when either side is missing.
            self._logger.info("Skipping re-grab: Prowlarr or qBittorrent is not configured")
            return RegrabResult(skipped=True)

        releases = await self._repository.get_potential_outdated_releases(limit=self._batch_size)
        indexers_by_name = await self._regrapper.indexers_by_name()

        if not releases:
            # No release to attribute this to, so no `request_id`: the line is the
            # sweep's own outcome, findable on the logs page under the task filter.
            self._logger.info("No releases to check for updates")
            return RegrabResult()

        result = RegrabResult()
        last_check: dict[str, datetime] = {}

        for release in releases:
            try:
                await self._wait_for_indexer(release, last_check)
                if await self._regrapper.regrab(release, indexers_by_name):
                    result.regrabbed += 1
                result.checked += 1
            except Exception as exc:
                result.failed += 1
                # Bound per request id so a failed re-grab is visible on the
                # request left holding the stale release, not just in the
                # scheduler's own log.
                for request_id in release.request_ids or ["unknown"]:
                    self._logger.opt(exception=exc).error(
                        f"Failed to re-grab release: {exc}",
                        request_id=request_id,
                        release_id=release.id,
                        release_name=release.name,
                        error=str(exc),
                    )
            finally:
                # Recorded whatever came of the check. A release the sweep only
                # looked at - blocked indexer, unknown indexer, no longer listed -
                # still counts as checked, or with a bounded batch it would hold
                # its place at the head of the list for every run after this one.
                await self._record_check(release, last_check)

        self._logger.info(
            "Re-grab sweep complete",
            checked=result.checked,
            regrabbed=result.regrabbed,
            failed=result.failed,
            candidates=len(releases),
        )
        return result

    async def _wait_for_indexer(
        self,
        release: ReleaseRecord,
        last_check: dict[str, datetime],
    ) -> None:
        """Hold a release back until its own indexer has had its gap.

        Per indexer rather than per run: the throttling being avoided is a
        tracker's own, so a backlog on one tracker must not hold up the rest. The
        gap is measured from the end of the previous check against that indexer,
        which is when its last search and any torrent fetch had finished.
        """

        previous = last_check.get(self._indexer_key(release))
        if previous is None:
            return
        wait = self._indexer_delay_seconds - (self._clock() - previous).total_seconds()
        if wait > 0:
            await self._sleep(wait)

    async def _record_check(
        self,
        release: ReleaseRecord,
        last_check: dict[str, datetime],
    ) -> None:
        """Stamp the release as checked, which is also its place in the rotation.

        Best-effort: failing to write the stamp costs the next run a repeated
        check, which is not worth failing a sweep that already did the work.
        """

        now = self._clock()
        last_check[self._indexer_key(release)] = now
        try:
            await self._repository.update_release(release.id, regrab_checked_at=now)
        except Exception as exc:
            self._logger.warning(
                "Could not record the re-grab check",
                release_id=release.id,
                error=str(exc),
            )

    def _indexer_key(self, release: ReleaseRecord) -> str:
        """The tracker a check on this release would go to."""

        return (release.torrent_source or "").lower()


__all__ = [
    "DEFAULT_BATCH_SIZE",
    "DEFAULT_INDEXER_DELAY_SECONDS",
    "RegrabOutdatedReleasesUseCase",
    "RegrabResult",
]
