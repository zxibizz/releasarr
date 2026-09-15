"""Use case for re-grabbing releases that have been updated on the indexer."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING

from src.application.interfaces.indexers import IndexerDirectory
from src.application.interfaces.releases import (
    ReleaseDownloadService,
    ReleaseRepository,
    ReleaseSearchService,
)
from src.application.interfaces.request_warnings import RequestWarningRepository
from src.application.use_cases.releases.regrab import ReleaseRegrapper
from src.application.use_cases.requests.recompute_state import RecomputeRequestStateUseCase
from src.core.logging import get_logger

if TYPE_CHECKING:
    from loguru import Logger


class RegrabOutdatedReleasesUseCase:
    """Check every candidate release for updates (e.g. repacks) and re-download them.

    This is the sweep; the check on a single release lives in `ReleaseRegrapper`,
    which the on-demand refresh on a request drives as well.
    """

    def __init__(
        self,
        repository: ReleaseRepository,
        search_service: ReleaseSearchService,
        download_service: ReleaseDownloadService,
        warning_repository: RequestWarningRepository,
        recompute_state: RecomputeRequestStateUseCase,
        directory: IndexerDirectory,
        logger: Logger | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._search_service = search_service
        self._download_service = download_service
        self._logger = logger or get_logger(component="regrab_outdated_releases")
        self._regrapper = ReleaseRegrapper(
            repository=repository,
            search_service=search_service,
            download_service=download_service,
            warning_repository=warning_repository,
            recompute_state=recompute_state,
            directory=directory,
            logger=self._logger,
            clock=clock,
        )

    async def execute(self) -> None:
        """Process potential outdated releases."""
        if not self._search_service.is_configured or not self._download_service.is_configured:
            # A re-grab is a search plus a download, so there is nothing to check
            # and nothing to reach for when either side is missing.
            self._logger.info("Skipping re-grab: Prowlarr or qBittorrent is not configured")
            return

        releases = await self._repository.get_potential_outdated_releases()
        indexers_by_name = await self._regrapper.indexers_by_name()

        for release in releases:
            try:
                await self._regrapper.regrab(release, indexers_by_name)
            except Exception as exc:
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


__all__ = ["RegrabOutdatedReleasesUseCase"]
