"""Domain enumerations derived from the OpenAPI contract."""

from __future__ import annotations

from enum import Enum


class StrEnum(str, Enum):
    """Base class ensuring enum values behave like strings."""

    def __str__(self) -> str:  # pragma: no cover - trivial wrapper
        return str(self.value)


class MediaType(StrEnum):
    MOVIE = "movie"
    SERIES = "series"


class MediaRequestStatus(StrEnum):
    PENDING = "pending"
    SEARCHING = "searching"
    DOWNLOADING = "downloading"
    MONITORING = "monitoring"
    IMPORTING = "importing"
    COMPLETED = "completed"
    FAILED = "failed"


class ReleaseStatus(StrEnum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"


class RequestWarningCode(StrEnum):
    """A condition worth surfacing on a request but not worth blocking on.

    Stored per (request, release) pair: a release-scoped code like
    ``MAPPING_OVERLAP`` also answers "what is wrong with this release", while a
    request-only code like ``REGRAB_INDEXER_UNAVAILABLE`` leaves ``release_id``
    on the row filled in too, since a release is still what failed to answer.
    """

    MAPPING_OVERLAP = "mapping_overlap"
    REGRAB_INDEXER_UNAVAILABLE = "regrab_indexer_unavailable"
    RELEASE_NOT_LISTED = "release_not_listed"
    # A re-grab downloaded a replacement whose new files automapping could not
    # resolve, so the release needs a human before it can be imported.
    REGRAB_FILES_UNMAPPED = "regrab_files_unmapped"
    # A re-grab was abandoned: the replacement torrent does not contain every
    # file the release already has, which a healthy repack does.
    REGRAB_FILES_MISSING = "regrab_files_missing"


class ExistingReleasesAction(StrEnum):
    """What to do with a request's other releases when grabbing a new one."""

    KEEP = "keep"
    REPLACE = "replace"


class EpisodeStatus(StrEnum):
    """Where a single episode of a requested season stands.

    ``MISSING`` is the only one of the three that is anybody's to act on: it has
    aired and Sonarr holds no file for it, which is precisely what a release is
    grabbed to fix. An unaired episode is nothing to chase yet.
    """

    DOWNLOADED = "downloaded"
    MISSING = "missing"
    UNAIRED = "unaired"


class RequestLogLevel(StrEnum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class LogService(StrEnum):
    """Which process wrote a log record.

    The API and the scheduler run as separate processes that share one log file,
    so every record names the process that produced it.
    """

    API = "api"
    SCHEDULER = "scheduler"


class LogComponent(StrEnum):
    """Which part of the codebase wrote a log record.

    Closed rather than free-form so the logs page can enumerate the values and
    a mistyped one fails a type check instead of silently fragmenting the
    filter. The dotted prefix is a stable grouping the UI leans on: everything
    under one prefix shares one colour and one filter group.
    """

    API_HTTP = "api.http"
    API_ERROR = "api.error"
    API_AUTH = "api.auth"

    SCHEDULER = "scheduler"
    SCHEDULER_JOBS = "scheduler.jobs"

    TASK_RELEASE_SYNC = "task.release_sync"

    USECASE_ADD_REQUEST = "usecase.add_request"
    USECASE_AUTO_MAPPING = "usecase.auto_mapping"
    USECASE_AUTH = "usecase.auth"
    USECASE_CREATE_RELEASE = "usecase.create_release"
    USECASE_DELETE_RELEASE = "usecase.delete_release"
    USECASE_DELETE_REQUEST = "usecase.delete_request"
    USECASE_ENQUEUE_JOB = "usecase.enqueue_job"
    USECASE_EXPORT = "usecase.export"
    USECASE_FILE_MAPPINGS = "usecase.file_mappings"
    USECASE_GRAB = "usecase.grab"
    USECASE_INDEXERS = "usecase.indexers"
    USECASE_QUEUE_DOWNLOAD = "usecase.queue_download"
    USECASE_QUEUE_MANUAL = "usecase.queue_manual"
    USECASE_RECOMPUTE_STATE = "usecase.recompute_state"
    USECASE_REFRESH_RELEASES = "usecase.refresh_releases"
    USECASE_REGRAB = "usecase.regrab"
    USECASE_REGRAB_OUTDATED = "usecase.regrab_outdated"
    USECASE_RELEASE_SEARCH = "usecase.release_search"
    USECASE_REPLACE_EXISTING = "usecase.replace_existing"
    USECASE_SEARCH_MEDIA = "usecase.search_media"
    USECASE_SYNC_RADARR = "usecase.sync_radarr"
    USECASE_SYNC_SONARR = "usecase.sync_sonarr"
    USECASE_UPDATE_SEASONS = "usecase.update_seasons"
    USECASE_USERS = "usecase.users"

    INTEGRATION_PROWLARR = "integration.prowlarr"
    INTEGRATION_QBITTORRENT = "integration.qbittorrent"
    INTEGRATION_RADARR = "integration.radarr"
    INTEGRATION_SONARR = "integration.sonarr"
    INTEGRATION_TMDB = "integration.tmdb"
    INTEGRATION_TVDB = "integration.tvdb"


class IndexerHealth(StrEnum):
    """How usable an indexer is right now.

    Prowlarr distinguishes a user switching an indexer off from its own
    escalating back-off after repeated failures. Only the latter resolves on its
    own, and only the latter is worth alerting about.
    """

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    BLOCKED = "blocked"
    DISABLED = "disabled"


class UserRole(StrEnum):
    """A user's role. Admin bypasses every per-user permission flag."""

    ADMIN = "admin"
    USER = "user"


class IndexerEventType(StrEnum):
    """What an indexer was asked to do, in Prowlarr's own history.

    Prowlarr names these in camel case; they are renamed here to read like the
    rest of this codebase, and ``UNKNOWN`` absorbs any event type a newer
    Prowlarr starts reporting.
    """

    UNKNOWN = "unknown"
    INDEXER_QUERY = "indexer_query"
    INDEXER_RSS = "indexer_rss"
    INDEXER_AUTH = "indexer_auth"
    INDEXER_INFO = "indexer_info"
    RELEASE_GRABBED = "release_grabbed"


class IndexerLogLevel(StrEnum):
    """Severity in a search provider's own log, least severe first.

    Declared in order because the provider filters on this as a threshold: a
    request for warnings is expected to return errors too.
    """

    TRACE = "trace"
    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"
    FATAL = "fatal"


class AsyncJobStatus(StrEnum):
    QUEUED = "queued"
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class SyncJobKind(StrEnum):
    """A single unit of background work, runnable on a schedule or on demand."""

    SONARR_SYNC = "sonarr_sync"
    RADARR_SYNC = "radarr_sync"
    RELEASE_SYNC = "release_sync"
    EXPORT = "export"
    REGRAB = "regrab"


class SyncJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class SyncJobTrigger(StrEnum):
    """Who asked for the sync."""

    API = "api"
    DOWNLOAD_CLIENT = "download_client"
    SCHEDULE = "schedule"


__all__ = [
    "AsyncJobStatus",
    "EpisodeStatus",
    "IndexerEventType",
    "IndexerHealth",
    "IndexerLogLevel",
    "LogService",
    "MediaRequestStatus",
    "MediaType",
    "ReleaseStatus",
    "RequestLogLevel",
    "SyncJobKind",
    "SyncJobStatus",
    "SyncJobTrigger",
]
