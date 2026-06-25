"""Command objects consumed by request use cases."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.domain.enums import MediaRequestStatus, MediaType
from src.application.interfaces.media_requests import MediaLocalization


class _Unset:
    """Sentinel used to distinguish omitted fields from explicit null assignments."""

    __slots__ = ()


UNSET = _Unset()
"""Singleton sentinel value."""


@dataclass(slots=True)
class ListRequestsOptions:
    page: int | None = None
    per_page: int | None = None
    status: MediaRequestStatus | None = None
    media_type: MediaType | None = None


@dataclass(slots=True)
class CreateMovieRequestCommand:
    title: str
    year: int
    runtime: int
    imdb_id: str
    overview: str | None = None
    poster_url: str | None = None
    genres: list[str] | None = None
    localizations: dict[str, MediaLocalization] | None = None


@dataclass(slots=True)
class CreateSeriesRequestCommand:
    title: str
    year: int
    season_number: int
    total_episodes: int
    series_title: str
    series_year: int
    imdb_id: str
    overview: str | None = None
    poster_url: str | None = None
    genres: list[str] | None = None
    localizations: dict[str, MediaLocalization] | None = None


CreateMediaRequestCommand = CreateMovieRequestCommand | CreateSeriesRequestCommand


@dataclass(slots=True)
class UpdateMediaRequestCommand:
    title: str | None | _Unset = field(default=UNSET)
    year: int | _Unset = field(default=UNSET)
    poster_url: str | None | _Unset = field(default=UNSET)
    overview: str | None | _Unset = field(default=UNSET)
    genres: list[str] | None | _Unset = field(default=UNSET)
    status: MediaRequestStatus | _Unset = field(default=UNSET)
    runtime: int | None | _Unset = field(default=UNSET)
    imdb_id: str | None | _Unset = field(default=UNSET)
    season_number: int | None | _Unset = field(default=UNSET)
    total_episodes: int | None | _Unset = field(default=UNSET)
    series_title: str | None | _Unset = field(default=UNSET)
    series_year: int | None | _Unset = field(default=UNSET)
    localizations: dict[str, MediaLocalization] | None | _Unset = field(default=UNSET)

    def is_empty(self) -> bool:
        """Return True when no field was supplied in the update payload."""

        for value in self.__dict__.values():
            if value is not UNSET:
                return False
        return True


__all__ = [
    "UNSET",
    "CreateMediaRequestCommand",
    "CreateMovieRequestCommand",
    "CreateSeriesRequestCommand",
    "ListRequestsOptions",
    "UpdateMediaRequestCommand",
]
