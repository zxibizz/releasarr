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
    tvdb_id: int
    in_library: bool = False
    library_id: int | None = None
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


class AddRequestResponse(APIModel):
    """The requests created for the added media, one per season for a series."""

    requests: list[MediaRequest]


__all__ = [
    "AddRequestPayload",
    "AddRequestResponse",
    "MediaSearchResponse",
    "MediaSearchResult",
    "RootFolder",
    "RootFoldersResponse",
    "SeasonOption",
    "SeriesSeasonsResponse",
]
