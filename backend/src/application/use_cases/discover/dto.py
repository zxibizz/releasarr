"""DTOs returned by the add-request use cases."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.domain.enums import MediaRequestStatus, MediaType


@dataclass(slots=True)
class MediaSearchResultDTO:
    """A metadata provider match, annotated with what we already hold for it."""

    media_type: MediaType
    provider_id: int
    title: str
    year: int | None = None
    overview: str | None = None
    poster_url: str | None = None
    # Filled in from the Sonarr/Radarr lookup, which reports the library id of
    # anything already added.
    in_library: bool = False
    library_id: int | None = None
    # Series carry one request per season, movies at most one overall.
    requested_seasons: list[int] = field(default_factory=list)
    request_id: str | None = None
    request_status: MediaRequestStatus | None = None


@dataclass(slots=True)
class SeasonOptionDTO:
    """One season a series offers, with its library and request state."""

    season_number: int
    monitored: bool = False
    requested: bool = False
    request_id: str | None = None


@dataclass(slots=True)
class SeriesSeasonsDTO:
    """The seasons a series offers, and whether Sonarr already holds it."""

    # Absent when the seasons were read from a series in the library rather than
    # looked up by TVDB id, which is how the manage-seasons view arrives at them.
    tvdb_id: int | None = None
    in_library: bool = False
    library_id: int | None = None
    # Sonarr's series-wide flags, only meaningful for a series in the library;
    # it has nowhere to record either choice until then.
    monitored: bool = False
    monitor_new_seasons: bool = False
    seasons: list[SeasonOptionDTO] = field(default_factory=list)


@dataclass(slots=True)
class RootFolderDTO:
    """A library location a request can be added to."""

    path: str
    free_space: int | None = None


__all__ = [
    "MediaSearchResultDTO",
    "RootFolderDTO",
    "SeasonOptionDTO",
    "SeriesSeasonsDTO",
]
