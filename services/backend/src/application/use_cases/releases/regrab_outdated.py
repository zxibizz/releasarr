"""Use case for re-grabbing releases that have been updated on the indexer."""

from __future__ import annotations

import asyncio
from collections import Counter
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

# A check costs the tracker a search, so the sweep takes a bounded share of each
# indexer's backlog per run. What that share is depends on how much is waiting: a
# backlog small enough to fit the ceiling goes in one run, anything larger is
# spread over this many runs instead.
REGRAB_SPREAD_EXECUTIONS = 5
DEFAULT_MAX_REGRABS_PER_INDEXER_PER_EXECUTION = 20
DEFAULT_INDEXER_DELAY_SECONDS = 2.0


def _quota_for(count: int, *, executions: int, ceiling: int) -> int:
    """How many of one indexer's candidates a single run may check.

    A backlog that already fits the ceiling is not held back: spreading it would
    only delay a check that costs the tracker the same either way. Above that, an
    even share is taken, capped by the ceiling - so the whole set is covered in
    `executions` runs unless the ceiling makes that impossible.
    """

    if count <= ceiling:
        return count
    return min(-(-count // executions), ceiling)


@dataclass(slots=True)
class RegrabResult:
    """What one sweep did, for the task summary in the queue view."""

    checked: int = 0
    regrabbed: int = 0
    failed: int = 0
    # Candidates this run left for the next one, by design rather than failure.
    deferred: int = 0
    skipped: bool = False


class RegrabOutdatedReleasesUseCase:
    """Check candidate releases for updates (e.g. repacks) and re-download them.

    This is the sweep; the check on a single release lives in `ReleaseRegrapper`,
    which the on-demand refresh on a request drives as well.

    Trackers throttle a client that asks for too much at once, so the sweep is
    paced rather than exhaustive: each indexer gets a per-run allowance, and every
    run takes the releases that have waited longest, so its backlog spreads over
    the following runs. The ordering, not a stored queue, is what makes that fair.
    Two checks against the same indexer are additionally kept
    `indexer_delay_seconds` apart.
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
        max_per_indexer: int = DEFAULT_MAX_REGRABS_PER_INDEXER_PER_EXECUTION,
        indexer_delay_seconds: float = DEFAULT_INDEXER_DELAY_SECONDS,
        spread_executions: int = REGRAB_SPREAD_EXECUTIONS,
        sleeper: Callable[[float], Awaitable[None]] | None = None,
    ) -> None:
        self._repository = repository
        self._search_service = search_service
        self._download_service = download_service
        self._logger = logger or get_logger(LogComponent.USECASE_REGRAB_OUTDATED)
        self._clock = clock or (lambda: datetime.now(UTC))
        self._max_per_indexer = max(1, max_per_indexer)
        self._spread_executions = max(1, spread_executions)
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
        """Process this run's share of the potential outdated releases."""
        if not self._search_service.is_configured or not self._download_service.is_configured:
            # A re-grab is a search plus a download, so there is nothing to check
            # and nothing to reach for when either side is missing.
            self._logger.info("Skipping re-grab: Prowlarr or qBittorrent is not configured")
            return RegrabResult(skipped=True)

        releases = await self._repository.get_potential_outdated_releases()

        if not releases:
            # No release to attribute this to, so no `request_id`: the line is the
            # sweep's own outcome, findable on the logs page under the task filter.
            self._logger.info("No releases to check for updates")
            return RegrabResult()

        selected, deferred = self._select_batch(releases)
        indexers_by_name = await self._regrapper.indexers_by_name()

        result = RegrabResult(deferred=deferred)
        last_check: dict[str, datetime] = {}

        for release in selected:
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
                # still counts as checked, or it would spend its indexer's
                # allowance again on every run after this one.
                await self._record_check(release, last_check)

        self._logger.info(
            "Re-grab sweep complete",
            checked=result.checked,
            regrabbed=result.regrabbed,
            failed=result.failed,
            candidates=len(releases),
            deferred=deferred,
        )
        return result

    def _select_batch(self, releases: list[ReleaseRecord]) -> tuple[list[ReleaseRecord], int]:
        """This run's share of the backlog, a bounded number per indexer.

        Candidates arrive least recently checked first, so an indexer's own
        allowance goes to the releases that have waited longest. What is left over
        belongs to the next run - nothing is stored for it, the ordering is the
        queue.
        """

        counts = Counter(self._indexer_key(release) for release in releases)
        allowances = {
            key: _quota_for(
                count,
                executions=self._spread_executions,
                ceiling=self._max_per_indexer,
            )
            for key, count in counts.items()
        }

        selected: list[ReleaseRecord] = []
        taken: Counter[str] = Counter()
        for release in releases:
            key = self._indexer_key(release)
            if taken[key] < allowances[key]:
                taken[key] += 1
                selected.append(release)
        return selected, len(releases) - len(selected)

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
    "DEFAULT_INDEXER_DELAY_SECONDS",
    "DEFAULT_MAX_REGRABS_PER_INDEXER_PER_EXECUTION",
    "REGRAB_SPREAD_EXECUTIONS",
    "RegrabOutdatedReleasesUseCase",
    "RegrabResult",
]
