"""Read and change which seasons of a series releasarr holds requests for."""

from __future__ import annotations

from dataclasses import dataclass, field

from loguru._logger import Logger

from src.application.interfaces.media_requests import MediaRequestRepository
from src.application.interfaces.sonarr import SonarrService
from src.application.use_cases.discover.dto import SeasonOptionDTO, SeriesSeasonsDTO
from src.application.use_cases.discover.exceptions import (
    SeasonSelectionError,
    SeasonsUnmanageableError,
)
from src.application.use_cases.discover.request_state import requested_seasons_by_series
from src.application.use_cases.requests.exceptions import MediaRequestNotFoundError
from src.application.use_cases.requests.sync_sonarr import SyncSonarrMediaRequestsUseCase
from src.core.logging import get_logger
from src.domain.enums import MediaType


@dataclass(slots=True)
class UpdateRequestSeasonsCommand:
    """The seasons Sonarr should monitor for a series, as the user left them.

    ``monitored`` is the series flag. Left unset it is worked out from what the
    seasons are left wanting, which is what removing a single request relies on.
    """

    season_numbers: list[int] = field(default_factory=list)
    monitored: bool | None = None
    monitor_new_seasons: bool = False


async def _resolve_series_id(repository: MediaRequestRepository, request_id: str) -> int:
    """Return the Sonarr series a request belongs to.

    Seasons are reached through a request because that is the only handle the
    request page has: the row carries the Sonarr id the sync stamped on it, and
    nothing about TVDB.
    """

    record = await repository.get_request(request_id)
    if record is None:
        raise MediaRequestNotFoundError(request_id)
    if record.media_type != MediaType.SERIES:
        raise SeasonsUnmanageableError(f"Request '{request_id}' is a movie and has no seasons")
    if record.sonarr_series_id is None:
        raise SeasonsUnmanageableError(
            f"Request '{request_id}' is not linked to a series in Sonarr yet"
        )
    return record.sonarr_series_id


async def _describe_seasons(
    repository: MediaRequestRepository,
    sonarr: SonarrService,
    series_id: int,
) -> SeriesSeasonsDTO:
    details = await sonarr.get_series(series_id)
    requested = (await requested_seasons_by_series(repository)).get(series_id, {})

    return SeriesSeasonsDTO(
        tvdb_id=details.tvdb_id,
        in_library=True,
        library_id=series_id,
        monitored=details.monitored,
        monitor_new_seasons=details.monitor_new_seasons,
        seasons=[
            SeasonOptionDTO(
                season_number=season_number,
                monitored=season.monitored,
                requested=season_number in requested,
                request_id=requested.get(season_number),
            )
            for season_number, season in sorted(details.seasons.items())
        ],
    )


class ListRequestSeasonsUseCase:
    """Answer which seasons of a request's series Sonarr monitors.

    Sonarr is asked by series id rather than through a TVDB lookup, which is both
    what the request knows and one round trip fewer: a request only carries a
    series id once the sync has seen the series, so the library question the
    discover endpoint has to settle is already answered here.
    """

    def __init__(
        self,
        *,
        repository: MediaRequestRepository,
        sonarr_service: SonarrService,
    ) -> None:
        self._repository = repository
        self._sonarr = sonarr_service

    async def execute(self, request_id: str) -> SeriesSeasonsDTO:
        series_id = await _resolve_series_id(self._repository, request_id)
        return await _describe_seasons(self._repository, self._sonarr, series_id)


class UpdateRequestSeasonsUseCase:
    """Bring a series' monitoring in line with the picked selection.

    The selection is Sonarr's monitoring, so the difference is taken against
    what Sonarr monitors now and not against the requests releasarr happens to
    hold. Those two part company routinely: a monitored season that is already
    complete never becomes a request, and diffing against requests would offer
    it up as unticked and then unmonitor it on save.

    Newly picked seasons are monitored and synced into requests exactly as the
    add-request flow does them; seasons dropped from the selection are
    unmonitored and any request of theirs deleted, because a request removed
    while Sonarr still wants its season comes back on the next sync.

    Both halves go through a single Sonarr write, so the series never passes
    through a state where it has been emptied of seasons and is about to be
    filled again - which is the moment Sonarr would see as "unmonitor me".
    """

    def __init__(
        self,
        *,
        repository: MediaRequestRepository,
        sonarr_service: SonarrService,
        sync_sonarr: SyncSonarrMediaRequestsUseCase,
        logger: Logger | None = None,
    ) -> None:
        self._repository = repository
        self._sonarr = sonarr_service
        self._sync_sonarr = sync_sonarr
        self._logger = logger or get_logger(component="update_request_seasons")

    async def execute(
        self,
        request_id: str,
        command: UpdateRequestSeasonsCommand,
    ) -> SeriesSeasonsDTO:
        series_id = await _resolve_series_id(self._repository, request_id)
        details = await self._sonarr.get_series(series_id)
        requested = (await requested_seasons_by_series(self._repository)).get(series_id, {})

        # Specials are outside what the picker offers, so a request for them is
        # neither added nor taken away by a selection that cannot mention them.
        desired = {season for season in command.season_numbers if season > 0}
        unknown = sorted(desired - set(details.seasons))
        if unknown:
            missing = ", ".join(str(season) for season in unknown)
            raise SeasonSelectionError(f"'{details.title}' has no season {missing}")

        monitored_now = {
            season_number
            for season_number, season in details.seasons.items()
            if season.monitored and season_number > 0
        }
        added = sorted(desired - monitored_now)
        removed = sorted(monitored_now - desired)

        await self._sonarr.apply_season_monitoring(
            series_id,
            monitor=added,
            unmonitor=removed,
            monitored=command.monitored,
            monitor_new_seasons=command.monitor_new_seasons,
        )

        if added:
            # A season Sonarr has only just started monitoring can still be
            # short of episodes, and a request built now would record it empty.
            await self._sonarr.wait_for_series_episodes(series_id, added)
            await self._sync_sonarr.sync_series(series_id, added)

        # Only the seasons that had a request to begin with; the rest were
        # monitored without ever going missing.
        dropped = [requested[season] for season in removed if season in requested]
        for dropped_request_id in dropped:
            await self._repository.delete_request(dropped_request_id)

        self._logger.info(
            "Updated season monitoring",
            request_id=request_id,
            sonarr_series_id=series_id,
            added=added,
            removed=removed,
            deleted_requests=dropped,
            monitored=command.monitored,
            monitor_new_seasons=command.monitor_new_seasons,
        )
        return await _describe_seasons(self._repository, self._sonarr, series_id)


__all__ = [
    "ListRequestSeasonsUseCase",
    "UpdateRequestSeasonsCommand",
    "UpdateRequestSeasonsUseCase",
]
