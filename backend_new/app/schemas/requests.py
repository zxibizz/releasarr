from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.request import RequestStatus, RequestType


class BaseRequestSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    year: int | None = None
    poster_url: str | None = None
    overview: str | None = None
    genres: list[str] = Field(default_factory=list)
    status: RequestStatus = RequestStatus.PENDING
    created_at: datetime
    updated_at: datetime


class MovieRequestSchema(BaseRequestSchema):
    type: Literal[RequestType.MOVIE] = RequestType.MOVIE
    runtime: int | None = None
    imdb_id: str | None = None


class SeriesRequestSchema(BaseRequestSchema):
    type: Literal[RequestType.SERIES] = RequestType.SERIES
    season_number: int | None = None
    total_episodes: int | None = None
    series_title: str | None = None
    series_year: int | None = None
    imdb_id: str | None = None


MediaRequestSchema = MovieRequestSchema | SeriesRequestSchema


class RequestsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    requests: list[MediaRequestSchema]
    total: int
    page: int
    per_page: int


class NewMediaRequest(BaseModel):
    type: Literal[RequestType.MOVIE, RequestType.SERIES]
    title: str
    year: int | None = None
    poster_url: str | None = None
    overview: str | None = None
    genres: list[str] = Field(default_factory=list)
    imdb_id: str | None = None
    runtime: int | None = None
    season_number: int | None = None
    total_episodes: int | None = None
    series_title: str | None = None
    series_year: int | None = None


class UpdateMediaRequest(BaseModel):
    title: str | None = None
    year: int | None = None
    poster_url: str | None = None
    overview: str | None = None
    genres: list[str] | None = None
    imdb_id: str | None = None
    runtime: int | None = None
    season_number: int | None = None
    total_episodes: int | None = None
    series_title: str | None = None
    series_year: int | None = None
    status: RequestStatus | None = None
