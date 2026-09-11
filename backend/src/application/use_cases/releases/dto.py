"""Data transfer objects returned by release use cases."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.domain.enums import ReleaseStatus


@dataclass(slots=True)
class ReleaseFileMappingDTO:
    mapping_type: str | None
    request_id: str | None
    request_title: str | None
    season: int | None
    episode: int | None


@dataclass(slots=True)
class ReleaseFileDTO:
    id: str
    name: str
    size_bytes: int
    path: str
    request_mapping: ReleaseFileMappingDTO | None


@dataclass(slots=True)
class ReleaseDTO:
    id: str
    name: str
    info_hash: str
    size_bytes: int
    files: list[ReleaseFileDTO]
    status: ReleaseStatus
    progress: float
    download_speed: float
    upload_speed: float
    seeders: int
    leechers: int
    ratio: float
    added_at: datetime
    completed_at: datetime | None
    request_ids: list[str]
    torrent_source: str | None
    quality: str | None


@dataclass(slots=True)
class ReleasesPageDTO:
    releases: list[ReleaseDTO]
    total: int
    page: int
    per_page: int


@dataclass(slots=True)
class ReleaseSearchResultDTO:
    release_id: str
    release_name: str
    size: str
    magnet_link: str | None
    torrent_file_url: str | None
    info_url: str | None
    seeders: int | None
    leechers: int | None
    quality: str | None
    source: str | None
    request_id: str | None


@dataclass(slots=True)
class ReleaseSearchResponseDTO:
    results: list[ReleaseSearchResultDTO]
    query: str
    total_results: int


@dataclass(slots=True)
class AsyncOperationDTO:
    operation: str
    status: str
    operation_id: str | None
    location: str | None
    message: str | None
    resource_id: str | None
    details: dict[str, object] | None


__all__ = [
    "AsyncOperationDTO",
    "ReleaseDTO",
    "ReleaseFileDTO",
    "ReleaseFileMappingDTO",
    "ReleaseSearchResponseDTO",
    "ReleaseSearchResultDTO",
    "ReleasesPageDTO",
]
