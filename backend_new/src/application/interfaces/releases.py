"""Interfaces supporting release management use cases."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from src.domain.enums import MediaType, ReleaseStatus


@dataclass(slots=True)
class ReleaseFileMapping:
    """Mapping metadata for a single release file."""

    mapping_type: MediaType | None
    request_id: str | None
    request_title: str | None
    season: int | None
    episode: int | None


@dataclass(slots=True)
class ReleaseFileRecord:
    """Normalized representation of a release file."""

    id: str
    name: str
    size_bytes: int
    path: str
    mapping: ReleaseFileMapping | None


@dataclass(slots=True)
class ReleaseRecord:
    """Normalized representation of a release with its files."""

    id: str
    name: str
    info_hash: str
    size_bytes: int
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
    files: list[ReleaseFileRecord]


@dataclass(slots=True)
class CreateReleaseData:
    """Payload required to register a new release."""

    magnet_link: str
    request_ids: list[str]
    name: str
    id: str
    source: str
    quality: str


@dataclass(slots=True)
class FileMappingUpdateData:
    """Payload describing a single file mapping update."""

    file_id: str
    mapping: ReleaseFileMapping | None


@dataclass(slots=True)
class ReleaseSearchResultRecord:
    """Individual search result for a potential release source."""

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
class ReleaseSearchResults:
    """Aggregate search results for a query."""

    results: list[ReleaseSearchResultRecord]
    query: str
    total_results: int


@dataclass(slots=True)
class QueuedDownload:
    """Descriptor for an asynchronous release download operation."""

    operation: str
    status: str
    operation_id: str | None
    location: str | None
    message: str | None
    resource_id: str | None
    details: dict[str, object] | None


class ReleaseRepository(Protocol):
    """Persistence operations for releases."""

    async def list_releases(
        self,
        *,
        page: int,
        per_page: int,
        status: ReleaseStatus | None,
        request_id: str | None,
    ) -> tuple[list[ReleaseRecord], int]:
        """Return paginated releases matching the provided filters."""

    async def create_release(self, data: CreateReleaseData) -> ReleaseRecord:
        """Persist a new release and return its stored representation."""

    async def get_release(self, release_id: str) -> ReleaseRecord | None:
        """Fetch a single release by identifier."""

    async def delete_release(self, release_id: str) -> bool:
        """Delete a release. Returns True when a record was removed."""

    async def update_file_mappings(
        self,
        release_id: str,
        updates: list[FileMappingUpdateData],
    ) -> bool:
        """Apply file mapping updates. Returns True on success."""


class ReleaseLifecycleService(Protocol):
    """Control operations for pausing/resuming release downloads."""

    async def pause(self, release_id: str) -> bool:
        """Attempt to pause a release download. Returns True when applied."""

    async def resume(self, release_id: str) -> bool:
        """Attempt to resume a release download. Returns True when applied."""


class ReleaseSearchService(Protocol):
    """External search interface for release sources."""

    async def search(self, query: str, request_id: str | None = None) -> ReleaseSearchResults:
        """Search for releases matching the supplied query."""

    def resolve(self, release_id: str) -> ReleaseSearchResultRecord | None:
        """Return a previously cached search result by identifier, when available."""

    async def fetch_torrent(self, url: str) -> bytes:
        """Download raw torrent data for a release candidate."""


class ReleaseDownloadService(Protocol):
    """Queue releases for download operations."""

    async def queue_download(self, request_id: str, release_id: str) -> QueuedDownload:
        """Queue a release download for the provided request identifier."""


__all__ = [
    "CreateReleaseData",
    "FileMappingUpdateData",
    "QueuedDownload",
    "ReleaseDownloadService",
    "ReleaseFileMapping",
    "ReleaseFileRecord",
    "ReleaseLifecycleService",
    "ReleaseRecord",
    "ReleaseRepository",
    "ReleaseSearchResultRecord",
    "ReleaseSearchResults",
    "ReleaseSearchService",
]
