"""Schemas for the add-request endpoints."""

from __future__ import annotations

from pydantic import Field

from src.schemas.base import APIModel
from src.schemas.enums import MediaRequestStatus, MediaType
from src.schemas.requests import MediaRequest


class MediaSearchResult(APIModel):
    """A metadata provider match, annotated with what releasarr already holds."""

    type: MediaType
    # The TVDB id for series, the TMDB id for movies: whichever the add needs.
    provider_id: int
    title: str
    year: int | None = None
    overview: str | None = None
    poster_url: str | None = None
    in_library: bool = False
    library_id: int | None = None
    # Series carry one request per season, movies at most one overall.
    requested_seasons: list[int] = Field(default_factory=list)
    request_id: str | None = None
    request_status: MediaRequestStatus | None = None


class MediaSearchResponse(APIModel):
    results: list[MediaSearchResult]


class SeasonOption(APIModel):
    """One season a series offers, with its library and request state."""

    season_number: int
    monitored: bool = False
    requested: bool = False
    request_id: str | None = None


class SeriesSeasonsResponse(APIModel):
    # Absent when the seasons were read from a series in the library rather than
    # looked up by TVDB id, which is how managing an existing request arrives.
    tvdb_id: int | None = None
    in_library: bool = False
    library_id: int | None = None
    # Whether Sonarr should monitor seasons announced after the series was added.
    # Only meaningful in the library; Sonarr has nowhere to record it until then.
    monitor_new_seasons: bool = False
    seasons: list[SeasonOption]


class RootFolder(APIModel):
    path: str
    free_space: int | None = None


class RootFoldersResponse(APIModel):
    folders: list[RootFolder]


class AddRequestPayload(APIModel):
    """A picked search result, plus where and what to add of it."""

    type: MediaType
    provider_id: int
    root_folder_path: str = Field(min_length=1)
    # Required for series and rejected for movies; the route enforces both, so the
    # message names the media type rather than the field.
    season_numbers: list[int] | None = None
    # Series only, for the same reason.
    monitor_new_seasons: bool = False


class AddRequestResponse(APIModel):
    """The requests created for the added media, one per season for a series."""

    requests: list[MediaRequest]


class UpdateSeasonsPayload(APIModel):
    """The seasons a series should hold requests for, as the user left them.

    The selection is absolute rather than a delta: seasons named here are
    requested afterwards and seasons left out are not, so dropping one both
    unmonitors it in Sonarr and removes its request. Specials are out of scope
    and keep whatever they had.
    """

    season_numbers: list[int] = Field(default_factory=list)
    monitor_new_seasons: bool = False


__all__ = [
    "AddRequestPayload",
    "AddRequestResponse",
    "MediaSearchResponse",
    "MediaSearchResult",
    "RootFolder",
    "RootFoldersResponse",
    "SeasonOption",
    "SeriesSeasonsResponse",
    "UpdateSeasonsPayload",
]
