"""On-demand check of a request's releases against the indexers and the download client."""

from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING

from src.application.interfaces.media_requests import MediaRequestRepository
from src.application.interfaces.releases import (
    ReleaseDownloadService,
    ReleaseRecord,
    ReleaseRepository,
    ReleaseSearchService,
    ReleaseTorrentState,
    ReleaseWarning,
)
from src.application.interfaces.request_warnings import RequestWarningRepository
from src.application.use_cases.indexers.exceptions import ProwlarrNotConfiguredError
from src.application.use_cases.releases.commands import RefreshRequestReleasesCommand
from src.application.use_cases.releases.dto import ReleaseRefreshDTO
from src.application.use_cases.releases.exceptions import QbittorrentNotConfiguredError
from src.application.use_cases.releases.mappers import record_to_dto
from src.application.use_cases.releases.regrab import ReleaseRegrapper, is_regrabbable
from src.application.use_cases.releases.warnings import rows_to_release_warnings
from src.application.use_cases.requests.exceptions import MediaRequestNotFoundError
from src.application.use_cases.requests.recompute_state import RecomputeRequestStateUseCase
from src.core.logging import get_logger
from src.domain.enums import ReleaseStatus

if TYPE_CHECKING:
    from loguru import Logger

# A release in one of these states can still move, so its row is worth reading
# back from the client. Anything else is settled by the scheduled sync.
LIVE_STATUSES = frozenset({ReleaseStatus.PENDING, ReleaseStatus.DOWNLOADING})


class RefreshRequestReleasesUseCase:
    """Bring one request's releases up to date on demand.

    Two passes, because the two halves of a release's life need different
    sources: a finished release is only ever out of date when its indexer
    replaced the torrent, and a release still in flight is only ever out of date
    relative to what the download client currently reports.
    """

    def __init__(
        self,
        request_repository: MediaRequestRepository,
        release_repository: ReleaseRepository,
        warning_repository: RequestWarningRepository,
        download_service: ReleaseDownloadService,
        search_service: ReleaseSearchService,
        regrapper: ReleaseRegrapper,
        recompute_state: RecomputeRequestStateUseCase,
        logger: Logger | None = None,
    ) -> None:
        self._request_repository = request_repository
        self._release_repository = release_repository
        self._warning_repository = warning_repository
        self._download_service = download_service
        self._search_service = search_service
        self._regrapper = regrapper
        self._recompute_state = recompute_state
        self._logger = logger or get_logger(component="refresh_request_releases")

    async def execute(self, command: RefreshRequestReleasesCommand) -> ReleaseRefreshDTO:
        await self._guard_scope(command)

        # Each pass needs the download client: one to read a torrent's progress,
        # the other to hand a replacement to. Reporting success for the half that
        # could run would hide the half that could not.
        if not self._download_service.is_configured:
            raise QbittorrentNotConfiguredError
        if not self._search_service.is_configured:
            raise ProwlarrNotConfiguredError

        releases = await self._release_repository.get_releases_for_requests([command.request_id])

        regrabbed = await self._regrab_finished(command.request_id, releases)
        if regrabbed:
            # A re-grab rewrote those releases' hashes and put them back in flight,
            # so the status pass has to read the rows as they are now: asking about
            # the torrent they used to carry would answer for a download that no
            # longer exists, and skip the one that replaced it.
            releases = await self._release_repository.get_releases_for_requests(
                [command.request_id]
            )

        statuses_updated = await self._sync_statuses(command.request_id, releases)

        try:
            # Idempotent, and cheaper than reasoning about which pass already
            # settled what: a re-grab recomputes through the regrapper, the status
            # pass can move a release too, and either way the request's status,
            # freshness and overlap warnings should follow its releases now rather
            # than at the next scheduled sync.
            await self._recompute_state.execute([command.request_id])
        except Exception as exc:  # pragma: no cover - defensive
            self._logger.warning(
                "Failed to settle request after refresh",
                request_id=command.request_id,
                error=str(exc),
            )

        refreshed = await self._dtos(command)
        return ReleaseRefreshDTO(
            releases=[record_to_dto(record, warnings) for record, warnings in refreshed],
            statuses_updated=statuses_updated,
            regrabbed=len(regrabbed),
        )

    async def _guard_scope(self, command: RefreshRequestReleasesCommand) -> None:
        """Refuse a request the caller may not see, as a 404 rather than a 403.

        A refresh can re-grab, so the check has to happen before any of that
        runs rather than once a row is on its way back out.
        """

        request = await self._request_repository.get_request(command.request_id)
        if request is None or not command.scope.permits(request.owner_user_id):
            raise MediaRequestNotFoundError(command.request_id)

    async def _regrab_finished(
        self, request_id: str, releases: list[ReleaseRecord]
    ) -> list[ReleaseRecord]:
        """Look every finished release up again, re-downloading replaced torrents."""

        indexers_by_name = await self._regrapper.indexers_by_name()
        regrabbed: list[ReleaseRecord] = []

        for release in releases:
            if release.status is not ReleaseStatus.COMPLETED or not is_regrabbable(release):
                continue
            try:
                if not await self._regrapper.regrab(release, indexers_by_name):
                    continue
            except Exception as exc:
                # One release the indexer could not answer for must not cost the
                # request's other releases their refresh.
                self._logger.opt(exception=exc).warning(
                    f"Failed to re-grab release: {exc}",
                    request_id=request_id,
                    release_id=release.id,
                    release_name=release.name,
                    error=str(exc),
                )
                continue

            regrabbed.append(release)

        return regrabbed

    async def _sync_statuses(self, request_id: str, releases: list[ReleaseRecord]) -> int:
        """Write back what the client reports for the releases that can still move.

        A torrent the client does not know is left alone rather than failed: it
        can be a release downloaded outside releasarr, or one whose torrent was
        removed from the client long ago.
        """

        updated = 0
        for release in releases:
            if release.status not in LIVE_STATUSES:
                continue
            try:
                state = await self._download_service.get_torrent_state(release.info_hash)
            except Exception as exc:
                self._logger.warning(
                    "Failed to read torrent state",
                    request_id=request_id,
                    release_id=release.id,
                    error=str(exc),
                )
                continue
            if state is None:
                continue

            fields = self._fields_from_state(state, release)
            if all(getattr(release, name) == value for name, value in fields.items()):
                continue

            await self._release_repository.update_release(release.id, **fields)
            updated += 1

        return updated

    @staticmethod
    def _fields_from_state(state: ReleaseTorrentState, release: ReleaseRecord) -> dict[str, object]:
        fields = asdict(state)
        # Completion is stamped once: a release that already has a time keeps it
        # even if the client reports a later one, as a re-check after a restart.
        fields["completed_at"] = release.completed_at or state.completed_at
        return fields

    async def _dtos(
        self, command: RefreshRequestReleasesCommand
    ) -> list[tuple[ReleaseRecord, list[ReleaseWarning]]]:
        """The request's releases as they now stand, with their warnings."""

        refreshed = await self._release_repository.get_releases_for_requests([command.request_id])
        rows_by_release = await self._warning_repository.list_for_releases(
            [record.id for record in refreshed]
        )
        return [
            (record, rows_to_release_warnings(rows_by_release.get(record.id, ())))
            for record in refreshed
        ]


__all__ = ["LIVE_STATUSES", "RefreshRequestReleasesUseCase"]
