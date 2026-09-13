"""Data transfer structures produced by request use cases."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from src.application.interfaces.media_requests import MediaLocalization
from src.domain.enums import EpisodeStatus, MediaRequestStatus, MediaType


@dataclass(slots=True)
class BaseMediaRequestDTO:
    id: str
    title: str
    year: int
    poster_url: str
    overview: str
    genres: list[str]
    status: MediaRequestStatus
    created_at: datetime
    updated_at: datetime
    localizations: dict[str, MediaLocalization] = field(default_factory=dict)
    exported_at: datetime | None = None


@dataclass(slots=True)
class MovieRequestDTO(BaseMediaRequestDTO):
    type: MediaType = MediaType.MOVIE
    runtime: int = 0
    imdb_id: str = ""
    radarr_movie_id: int | None = None


@dataclass(slots=True)
class SeriesRequestDTO(BaseMediaRequestDTO):
    type: MediaType = MediaType.SERIES
    season_number: int = 0
    total_episodes: int = 0
    episode_counts: SeriesEpisodeCountsDTO | None = None
    series_title: str = ""
    series_year: int = 0
    imdb_id: str = ""
    sonarr_series_id: int | None = None


@dataclass(slots=True)
class SeriesEpisodeCountsDTO:
    """Derived episode counts for a requested season."""

    downloaded: int
    pending: int
    unaired: int


MediaRequestDTO = MovieRequestDTO | SeriesRequestDTO


@dataclass(slots=True)
class MediaRequestsPageDTO:
    requests: list[MediaRequestDTO]
    total: int
    page: int
    per_page: int


@dataclass(slots=True)
class SeasonEpisodeDTO:
    """One episode of a requested season, as Sonarr currently holds it."""

    episode_number: int
    title: str
    status: EpisodeStatus
    air_date: datetime | None = None
    file_size: int | None = None


@dataclass(slots=True)
class SeasonEpisodesDTO:
    """The episodes of the one season a request covers."""

    season_number: int
    episodes: list[SeasonEpisodeDTO] = field(default_factory=list)


__all__ = [
    "BaseMediaRequestDTO",
    "MediaRequestDTO",
    "MediaRequestsPageDTO",
    "MovieRequestDTO",
    "SeasonEpisodeDTO",
    "SeasonEpisodesDTO",
    "SeriesRequestDTO",
]
