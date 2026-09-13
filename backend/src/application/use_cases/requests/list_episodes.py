"""List the episodes of the season a request covers, with what became of each."""

from __future__ import annotations

from datetime import UTC, datetime

from src.application.interfaces.media_requests import MediaRequestRepository
from src.application.interfaces.sonarr import SonarrEpisode, SonarrService
from src.application.use_cases.discover.exceptions import SeasonsUnmanageableError
from src.application.use_cases.requests.dto import SeasonEpisodeDTO, SeasonEpisodesDTO
from src.application.use_cases.requests.exceptions import MediaRequestNotFoundError
from src.domain.enums import EpisodeStatus, MediaType


class ListRequestEpisodesUseCase:
    """Answer what the season a request covers is made of, episode by episode.

    A request carries only a count of episodes, which says how much of a season
    there is but nothing about which parts of it arrived. Sonarr holds that per
    episode, so it is asked directly rather than derived from the mappings of
    the releases grabbed: a season is just as likely to have been filled from
    outside releasarr, and the files Sonarr ended up with are the truth either
    way.
    """

    def __init__(
        self,
        *,
        repository: MediaRequestRepository,
        sonarr_service: SonarrService,
    ) -> None:
        self._repository = repository
        self._sonarr = sonarr_service

    async def execute(self, request_id: str) -> SeasonEpisodesDTO:
        record = await self._repository.get_request(request_id)
        if record is None:
            raise MediaRequestNotFoundError(request_id)
        if record.media_type != MediaType.SERIES or record.season_number is None:
            raise SeasonsUnmanageableError(f"Request '{request_id}' is a movie and has no episodes")
        if record.sonarr_series_id is None:
            raise SeasonsUnmanageableError(
                f"Request '{request_id}' is not linked to a series in Sonarr yet"
            )

        season_number = record.season_number
        episodes = await self._sonarr.get_episodes(record.sonarr_series_id)
        now = datetime.now(UTC)

        return SeasonEpisodesDTO(
            season_number=season_number,
            episodes=[
                SeasonEpisodeDTO(
                    episode_number=episode.episode_number,
                    title=episode.title,
                    status=self._status(episode, now),
                    air_date=episode.air_date,
                )
                for episode in sorted(
                    (episode for episode in episodes if episode.season_number == season_number),
                    key=lambda episode: episode.episode_number,
                )
            ],
        )

    def _status(self, episode: SonarrEpisode, now: datetime) -> EpisodeStatus:
        """Where the episode stands, the file it has outranking the date it has.

        An episode can hold a file before its air date passes - a premiere put
        out early, or a date Sonarr has wrong - and calling that one unaired
        would hide a file the user can see in their library.
        """

        if episode.has_file:
            return EpisodeStatus.DOWNLOADED
        # No date is treated as unaired rather than missing: an episode Sonarr
        # cannot place in time is not one it can be said to be late on.
        if episode.air_date is None or episode.air_date > now:
            return EpisodeStatus.UNAIRED
        return EpisodeStatus.MISSING


__all__ = ["ListRequestEpisodesUseCase"]
