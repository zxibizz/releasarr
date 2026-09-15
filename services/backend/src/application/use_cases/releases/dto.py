"""Data transfer objects returned by release use cases."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from src.domain.enums import ReleaseStatus, RequestWarningCode


@dataclass(slots=True)
class ReleaseFileMappingDTO:
    mapping_type: str | None
    request_id: str | None
    request_title: str | None
    season: int | None
    episode: int | None


@dataclass(slots=True)
class ReleaseFileMappingSuggestionDTO:
    """A mapping automapping would make for a file, offered rather than stored."""

    file_id: str
    request_mapping: ReleaseFileMappingDTO


@dataclass(slots=True)
class ReleaseWarningDTO:
    code: RequestWarningCode
    file_ids: list[str]
    related_release_ids: list[str]
    details: dict[str, object] | None = None


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
    info_url: str | None = None
    published_at: datetime | None = None
    warnings: list[ReleaseWarningDTO] = field(default_factory=list)


@dataclass(slots=True)
class ReleasesPageDTO:
    releases: list[ReleaseDTO]
    total: int
    page: int
    per_page: int


@dataclass(slots=True)
class ReleaseRefreshDTO:
    """What one on-demand check of a request's releases did."""

    releases: list[ReleaseDTO]
    statuses_updated: int
    regrabbed: int


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
    publish_date: datetime | None = None


@dataclass(slots=True)
class IndexerSearchFailureDTO:
    """One indexer that a search fan-out could not get an answer from."""

    indexer_id: int
    name: str
    reason: str


@dataclass(slots=True)
class ReleaseSearchResponseDTO:
    results: list[ReleaseSearchResultDTO]
    query: str
    total_results: int
    failed_indexers: list[IndexerSearchFailureDTO] = field(default_factory=list)
    searched_indexers: int = 0


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
    "IndexerSearchFailureDTO",
    "ReleaseDTO",
    "ReleaseFileDTO",
    "ReleaseFileMappingDTO",
    "ReleaseFileMappingSuggestionDTO",
    "ReleaseSearchResponseDTO",
    "ReleaseSearchResultDTO",
    "ReleasesPageDTO",
]
