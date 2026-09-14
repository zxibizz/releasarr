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
    COMPLETED = "completed"
    FAILED = "failed"


class ReleaseStatus(StrEnum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    SEEDING = "seeding"
    COMPLETED = "completed"
    FAILED = "failed"


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
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class LogService(StrEnum):
    """Which process wrote a log record.

    The API and the scheduler run as separate processes that share one log file,
    so every record names the process that produced it. An ad-hoc CLI task run
    counts as the scheduler: it executes the same work the loop does, without
    the loop.
    """

    API = "api"
    SCHEDULER = "scheduler"


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
