"""Schemas for media request endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import Field, field_serializer

from src.schemas.base import APIModel
from src.schemas.common import PaginatedResponse
from src.schemas.enums import MediaRequestStatus, MediaType


class BaseMediaRequest(APIModel):
    id: str
    title: str
    year: int
    poster_url: str
    overview: str
    genres: list[str]
    status: MediaRequestStatus
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    def _serialize_datetime(self, value: datetime) -> str:
        if value.tzinfo is None:  # default to UTC when the database returns naive values
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


class MovieRequest(BaseMediaRequest):
    type: Literal[MediaType.MOVIE.value]
    runtime: int
    imdb_id: str


class SeriesRequest(BaseMediaRequest):
    type: Literal[MediaType.SERIES.value]
    season_number: int
    total_episodes: int
    series_title: str
    series_year: int
    imdb_id: str
    sonarr_series_id: int | None = None


MediaRequest = Annotated[MovieRequest | SeriesRequest, Field(discriminator="type")]


class CreateMovieRequest(APIModel):
    type: Literal[MediaType.MOVIE.value]
    title: str
    year: int
    runtime: int
    imdb_id: str
    overview: str | None = None
    poster_url: str | None = None
    genres: list[str] | None = None


class CreateSeriesRequest(APIModel):
    type: Literal[MediaType.SERIES.value]
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


MediaRequestCreate = Annotated[
    CreateMovieRequest | CreateSeriesRequest,
    Field(discriminator="type"),
]


class MediaRequestUpdate(APIModel):
    title: str | None = None
    year: int | None = None
    poster_url: str | None = None
    overview: str | None = None
    genres: list[str] | None = None
    status: MediaRequestStatus | None = None
    runtime: int | None = None
    imdb_id: str | None = None
    season_number: int | None = None
    total_episodes: int | None = None
    series_title: str | None = None
    series_year: int | None = None


class RequestsResponse(PaginatedResponse):
    requests: list[MediaRequest]


__all__ = [
    "BaseMediaRequest",
    "CreateMovieRequest",
    "CreateSeriesRequest",
    "MediaRequest",
    "MediaRequestCreate",
    "MediaRequestUpdate",
    "MovieRequest",
    "RequestsResponse",
    "SeriesRequest",
]
