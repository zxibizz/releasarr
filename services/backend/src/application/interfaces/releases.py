"""Interfaces supporting release management use cases."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from src.domain.enums import MediaType, ReleaseStatus, RequestWarningCode

# A release's source is the indexer Prowlarr attributed it to, except for
# hand-supplied torrents, which have no indexer to go back to.
MANUAL_SOURCE = "manual"


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
class ReleaseRequestSnapshot:
    """Subset of request data needed for release operations."""

    id: str
    sonarr_series_id: int | None
    title: str
    media_type: MediaType | None = None
    season_number: int | None = None
    radarr_movie_id: int | None = None
    year: int | None = None
    # Every title the request is known by. A movie's own title is whichever
    # language won the localization, so matching a release named in another
    # language needs the alternatives too.
    alternate_titles: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ReleaseWarning:
    """A condition worth surfacing on a release but not worth blocking on."""

    code: RequestWarningCode
    file_ids: list[str]
    related_release_ids: list[str]
    details: dict[str, object] | None = None


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
    requests: list[ReleaseRequestSnapshot]
    torrent_source: str | None
    quality: str | None
    files: list[ReleaseFileRecord]
    last_exported_info_hash: str | None
    export_failures_count: int
    info_url: str | None = None
    published_at: datetime | None = None


@dataclass(slots=True)
class CreateReleaseData:
    """Payload required to register a new release."""

    magnet_link: str
    request_ids: list[str]
    name: str
    id: str
    source: str
    quality: str
    files: list[ReleaseFileRecord] | None = None
    info_url: str | None = None
    published_at: datetime | None = None


@dataclass(slots=True)
class FileMappingUpdateData:
    """Payload describing a single file mapping update."""

    file_id: str
    mapping: ReleaseFileMapping | None


@dataclass(slots=True)
class FileReconciliation:
    """How a release's stored files line up with a replacement torrent's files.

    ``matched`` pairs the id of each surviving stored file with the incoming file
    that takes its place, ``added`` holds the files the release did not have, and
    ``missing`` the stored files the torrent no longer carries - which a caller
    refuses over rather than deleting, since a replacement dropping a file is not
    a shape a healthy repack has.
    """

    matched: list[tuple[str, ReleaseFileRecord]]
    added: list[ReleaseFileRecord]
    missing: list[ReleaseFileRecord]


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
    publish_date: datetime | None = None


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


@dataclass(slots=True)
class ReleaseTorrentState:
    """Live state of one release's torrent as the download client reports it."""

    progress: float
    download_speed: float
    upload_speed: float
    seeders: int
    leechers: int
    ratio: float
    size_bytes: int
    status: ReleaseStatus
    # The client's own completion time, which a caller only adopts when the
    # release has none stamped yet.
    completed_at: datetime | None


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

    async def unlink_request(self, release_id: str, request_id: str) -> bool:
        """Detach a request from a release without touching the release itself.

        Used when replacing a request's releases: a release shared with other
        requests must survive, only the link to this one goes.
        """

    async def get_releases_for_requests(self, request_ids: list[str]) -> list[ReleaseRecord]:
        """Fetch every release linked to any of the given requests, unpaginated.

        Used to evaluate cross-release conditions (mapping overlaps, existing
        grabs) that a single release's own row cannot answer.
        """

    async def list_request_ids_with_releases(self) -> list[str]:
        """Every request id that has at least one release, for the warning reconcile pass."""

    async def update_file_mappings(
        self,
        release_id: str,
        updates: list[FileMappingUpdateData],
    ) -> bool:
        """Apply file mapping updates. Returns True on success."""

    async def sync_release_files(
        self,
        release_id: str,
        reconciliation: FileReconciliation,
    ) -> list[ReleaseFileRecord] | None:
        """Bring a release's file rows in line with a replacement torrent.

        Matched rows are repointed at the file that replaces them and keep every
        mapping column; added files are inserted unmapped. Returns the release's
        files as they now stand, or None when there is no such release.
        """

    async def get_finished_not_exported(self) -> list[ReleaseRecord]:
        """Fetch completed releases that haven't been exported to Sonarr."""

    async def get_potential_outdated_releases(self) -> list[ReleaseRecord]:
        """Fetch completed releases that might have better versions available.

        A release that already refused its replacement is left out: re-checking it
        on every pass cannot change the indexer's answer, and the file list the
        check fetches is not free. The on-demand refresh on its request still
        checks it, and a replacement that finally carries every stored file clears
        the refusal and puts the release back in the sweep.
        """

    async def update_release(self, release_id: str, **kwargs: object) -> bool:
        """Update arbitrary fields of a release."""

    async def count_by_status(self) -> dict[ReleaseStatus, int]:
        """Return the number of releases grouped by status."""


class ReleaseLifecycleService(Protocol):
    """Control operations for pausing/resuming release downloads."""

    @property
    def is_configured(self) -> bool:
        """Whether a download client backs this service and can be reached."""

    async def pause(self, release_id: str) -> bool:
        """Attempt to pause a release download. Returns True when applied."""

    async def resume(self, release_id: str) -> bool:
        """Attempt to resume a release download. Returns True when applied."""


class ReleaseSearchUnavailableError(RuntimeError):
    """Raised when a search request could not be answered by its indexer(s)."""


class ReleaseSearchService(Protocol):
    """External search interface for release sources."""

    @property
    def is_configured(self) -> bool:
        """Whether a provider is set up to answer searches."""

    async def search(
        self,
        query: str,
        request_id: str | None = None,
        indexer_id: int | None = None,
    ) -> ReleaseSearchResults:
        """Search for releases matching the supplied query.

        ``indexer_id`` scopes the search to a single indexer; omitted, the
        provider sweeps every indexer it has configured.
        """

    def resolve(self, release_id: str) -> ReleaseSearchResultRecord | None:
        """Return a previously cached search result by identifier, when available."""

    async def fetch_torrent(self, url: str) -> bytes:
        """Download raw torrent data for a release candidate."""


class ReleaseDownloadService(Protocol):
    """Queue releases for download operations."""

    @property
    def is_configured(self) -> bool:
        """Whether a download client backs this service and can be reached."""

    async def queue_download(
        self,
        request_id: str,
        release_id: str,
        magnet_link: str,
        torrent_bytes: bytes | None = None,
    ) -> QueuedDownload:
        """Download a release for the provided request identifier."""

    async def delete_download(self, release_id: str) -> None:
        """Remove a release download from the client."""

    async def get_download_directory(self, info_hash: str) -> str | None:
        """Return the absolute directory the client downloaded a torrent into.

        Release file paths are stored relative to the torrent root, so this is what
        turns them into the absolute paths external importers require. Returns None
        when the client doesn't know the torrent.
        """

    async def get_torrent_state(self, info_hash: str) -> ReleaseTorrentState | None:
        """Read one torrent's current state, or None when the client has no such torrent."""


__all__ = [
    "MANUAL_SOURCE",
    "CreateReleaseData",
    "FileMappingUpdateData",
    "FileReconciliation",
    "QueuedDownload",
    "ReleaseDownloadService",
    "ReleaseFileMapping",
    "ReleaseFileRecord",
    "ReleaseLifecycleService",
    "ReleaseRecord",
    "ReleaseRepository",
    "ReleaseRequestSnapshot",
    "ReleaseSearchResultRecord",
    "ReleaseSearchResults",
    "ReleaseSearchService",
    "ReleaseSearchUnavailableError",
    "ReleaseTorrentState",
]
