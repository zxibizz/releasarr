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
    "MediaRequestStatus",
    "MediaType",
    "ReleaseStatus",
    "RequestLogLevel",
    "SyncJobKind",
    "SyncJobStatus",
    "SyncJobTrigger",
]
