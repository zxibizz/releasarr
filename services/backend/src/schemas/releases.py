"""Schemas for release management endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field

from src.schemas.base import APIModel
from src.schemas.common import PaginatedResponse
from src.schemas.enums import ExistingReleasesAction, ReleaseStatus, ReleaseWarningCode


class MovieFileRequestMapping(APIModel):
    mapping_type: Literal["movie"]
    request_id: str
    request_title: str | None = None


class SeriesFileRequestMapping(APIModel):
    mapping_type: Literal["series"]
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
    size: int = Field(validation_alias="size_bytes")
    path: str
    request_mapping: FileRequestMapping | None = None


class ReleaseWarning(APIModel):
    code: ReleaseWarningCode
    file_ids: list[str]
    related_release_ids: list[str]
    details: dict[str, object] | None = None


class Release(APIModel):
    id: str
    name: str
    hash: str = Field(validation_alias="info_hash")
    size: int = Field(validation_alias="size_bytes")
    files: list[ReleaseFile]
    status: ReleaseStatus
    progress: float
    download_speed: float
    upload_speed: float
    seeders: int
    leechers: int
    ratio: float
    added_date: datetime = Field(validation_alias="added_at")
    completed_date: datetime | None = Field(default=None, validation_alias="completed_at")
    request_ids: list[str]
    torrent_source: str | None = None
    quality: str | None = None
    info_url: str | None = None
    published_date: datetime | None = Field(default=None, validation_alias="published_at")
    warnings: list[ReleaseWarning] = Field(default_factory=list)


class ReleasesResponse(PaginatedResponse):
    releases: list[Release]


class ReleaseFileMappingInput(APIModel):
    file_id: str
    request_mapping: FileRequestMapping | None = None


class ReleaseFileMappingsUpdate(APIModel):
    files: list[ReleaseFileMappingInput]


class ReleaseFileMappingSuggestion(APIModel):
    """A mapping the server proposes for a file. Unlike an update, it always
    names one: there is no such thing as suggesting that a file be unmapped."""

    file_id: str
    request_mapping: FileRequestMapping


class ReleaseFileMappingSuggestions(APIModel):
    files: list[ReleaseFileMappingSuggestion]


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
    publish_date: datetime | None = None


class IndexerSearchFailure(APIModel):
    indexer_id: int
    name: str
    reason: str


class ReleaseSearchResponse(APIModel):
    results: list[ReleaseSearchResult]
    query: str
    total_results: int
    failed_indexers: list[IndexerSearchFailure] = Field(default_factory=list)
    searched_indexers: int = 0


class ReleaseDownloadRequest(APIModel):
    release_id: str
    existing_releases: ExistingReleasesAction | None = None


class ManualReleaseRequest(APIModel):
    """A hand-supplied grab: exactly one of the two fields must be present."""

    magnet_link: str | None = None
    torrent_file_base64: str | None = None
    existing_releases: ExistingReleasesAction | None = None


__all__ = [
    "AddReleaseRequest",
    "FileRequestMapping",
    "IndexerSearchFailure",
    "ManualReleaseRequest",
    "MovieFileRequestMapping",
    "Release",
    "ReleaseDownloadRequest",
    "ReleaseFile",
    "ReleaseFileMappingInput",
    "ReleaseFileMappingSuggestion",
    "ReleaseFileMappingSuggestions",
    "ReleaseFileMappingsUpdate",
    "ReleaseSearchResponse",
    "ReleaseSearchResult",
    "ReleaseWarning",
    "ReleasesResponse",
    "SeriesFileRequestMapping",
]
