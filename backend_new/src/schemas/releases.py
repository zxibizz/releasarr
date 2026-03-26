"""Schemas for release management endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field

from src.schemas.base import APIModel
from src.schemas.common import PaginatedResponse
from src.schemas.enums import MediaType, ReleaseStatus


class MovieFileRequestMapping(APIModel):
    mapping_type: Literal[MediaType.MOVIE.value]
    request_id: str
    request_title: str | None = None


class SeriesFileRequestMapping(APIModel):
    mapping_type: Literal[MediaType.SERIES.value]
    request_id: str
    request_title: str | None = None
    season: int
    episode: int


FileRequestMapping = Annotated[
    MovieFileRequestMapping | SeriesFileRequestMapping,
    Field(discriminator="mapping_type"),
]


class ReleaseFile(APIModel):
    id: str
    name: str
    size: int = Field(alias="size_bytes")
    path: str
    request_mapping: FileRequestMapping | None = None


class Release(APIModel):
    id: str
    name: str
    hash: str = Field(alias="info_hash")
    size: int = Field(alias="size_bytes")
    files: list[ReleaseFile]
    status: ReleaseStatus
    progress: float
    download_speed: float
    upload_speed: float
    seeders: int
    leechers: int
    ratio: float
    added_date: datetime = Field(alias="added_at")
    completed_date: datetime | None = Field(default=None, alias="completed_at")
    request_ids: list[str]
    torrent_source: str | None = None
    quality: str | None = None


class ReleasesResponse(PaginatedResponse):
    releases: list[Release]


class ReleaseFileMappingInput(APIModel):
    file_id: str
    request_mapping: FileRequestMapping | None = None


class ReleaseFileMappingsUpdate(APIModel):
    files: list[ReleaseFileMappingInput]


class AddReleaseRequest(APIModel):
    magnet_link: str
    request_ids: list[str]


class ReleaseSearchResult(APIModel):
    release_id: str
    release_name: str
    size: str
    magnet_link: str | None = None
    torrent_file_url: str | None = None
    info_url: str | None = None
    seeders: int | None = None
    leechers: int | None = None
    quality: str | None = None
    source: str | None = None
    request_id: str | None = None


class ReleaseSearchResponse(APIModel):
    results: list[ReleaseSearchResult]
    query: str
    total_results: int


class ReleaseDownloadRequest(APIModel):
    release_id: str


__all__ = [
    "AddReleaseRequest",
    "FileRequestMapping",
    "MovieFileRequestMapping",
    "Release",
    "ReleaseDownloadRequest",
    "ReleaseFile",
    "ReleaseFileMappingInput",
    "ReleaseFileMappingsUpdate",
    "ReleaseSearchResponse",
    "ReleaseSearchResult",
    "ReleasesResponse",
    "SeriesFileRequestMapping",
]
