"""Data transfer structures produced by request use cases."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from src.application.interfaces.media_requests import MediaLocalization
from src.domain.enums import MediaRequestStatus, MediaType


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


@dataclass(slots=True)
class MovieRequestDTO(BaseMediaRequestDTO):
    type: MediaType = MediaType.MOVIE
    runtime: int = 0
    imdb_id: str = ""


@dataclass(slots=True)
class SeriesRequestDTO(BaseMediaRequestDTO):
    type: MediaType = MediaType.SERIES
    season_number: int = 0
    total_episodes: int = 0
    series_title: str = ""
    series_year: int = 0
    imdb_id: str = ""
    sonarr_series_id: int | None = None


MediaRequestDTO = MovieRequestDTO | SeriesRequestDTO


@dataclass(slots=True)
class MediaRequestsPageDTO:
    requests: list[MediaRequestDTO]
    total: int
    page: int
    per_page: int


__all__ = [
    "BaseMediaRequestDTO",
    "MediaRequestDTO",
    "MediaRequestsPageDTO",
    "MovieRequestDTO",
    "SeriesRequestDTO",
]
