"""List the seasons a series offers, with their library and request state."""

from __future__ import annotations

from collections.abc import Sequence

from src.application.interfaces.media_requests import MediaRequestRepository
from src.application.interfaces.sonarr import SeriesDetails, SonarrService
from src.application.interfaces.tvdb import TvdbService
from src.application.use_cases.discover.dto import SeasonOptionDTO, SeriesSeasonsDTO
from src.application.use_cases.discover.exceptions import MediaNotFoundError
from src.application.use_cases.discover.request_state import requested_seasons_by_series
from src.domain.enums import MediaType


class ListSeasonOptionsUseCase:
    """Answer which seasons of a series can be requested, and which already are.

    Sonarr's by-id lookup is the source for the season list, so the numbers offered
    are the ones an add would actually monitor. It also settles the library
    question exactly, which the free-text search behind the result list can only
    approximate.
    """

    def __init__(
        self,
        *,
        repository: MediaRequestRepository,
        sonarr_service: SonarrService,
        tvdb_service: TvdbService | None,
        metadata_languages: Sequence[str] | None = None,
    ) -> None:
        self._repository = repository
        self._sonarr = sonarr_service
        self._tvdb = tvdb_service
        self._metadata_languages = tuple(metadata_languages or ())

    async def execute(self, tvdb_id: int) -> SeriesSeasonsDTO:
        lookup = await self._sonarr.lookup_series(tvdb_id)
        if lookup is None:
            return await self._from_tvdb(tvdb_id)

        series_id = lookup.existing_series_id
        if series_id is None:
            return SeriesSeasonsDTO(
                tvdb_id=tvdb_id,
                seasons=[
                    SeasonOptionDTO(season_number=season_number)
                    for season_number in lookup.season_numbers
                ],
            )

        # An added series knows more than the lookup does: the seasons carry the
        # monitoring the user has since set, and our own requests hang off it.
        details = await self._sonarr.get_series(series_id)
        requested = (await requested_seasons_by_series(self._repository)).get(series_id, {})
        season_numbers = sorted(set(details.seasons) | set(lookup.season_numbers))

        return SeriesSeasonsDTO(
            tvdb_id=tvdb_id,
            in_library=True,
            library_id=series_id,
            monitor_new_seasons=details.monitor_new_seasons,
            seasons=[
                SeasonOptionDTO(
                    season_number=season_number,
                    monitored=self._is_monitored(details, season_number),
                    requested=season_number in requested,
                    request_id=requested.get(season_number),
                )
                for season_number in season_numbers
            ],
        )

    async def _from_tvdb(self, tvdb_id: int) -> SeriesSeasonsDTO:
        """Fall back to TVDB's own season list when Sonarr has no match.

        Sonarr resolves ids through its own metadata server, which can lag behind
        TVDB for a series added there very recently. Offering TVDB's seasons keeps
        such a series pickable; the add itself still has to go through Sonarr.
        """

        if self._tvdb is None:
            raise MediaNotFoundError(MediaType.SERIES, tvdb_id)

        metadata = await self._tvdb.get_series(tvdb_id, self._metadata_languages)
        return SeriesSeasonsDTO(
            tvdb_id=tvdb_id,
            seasons=[
                SeasonOptionDTO(season_number=season_number) for season_number in metadata.seasons
            ],
        )

    def _is_monitored(self, details: SeriesDetails, season_number: int) -> bool:
        season = details.seasons.get(season_number)
        return bool(season and season.monitored)


__all__ = ["ListSeasonOptionsUseCase"]
