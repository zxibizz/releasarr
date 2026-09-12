"""SQLAlchemy ORM models representing the new Releasarr domain."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.db import Base
from src.domain.enums import (
    MediaRequestStatus,
    MediaType,
    ReleaseStatus,
    SyncJobKind,
    SyncJobStatus,
    SyncJobTrigger,
)

JSONDict = MutableDict.as_mutable(JSON)
JSONList = MutableList.as_mutable(JSON)


def build_enum(enum_cls: type[Enum], name: str) -> SAEnum:
    """Create an Enum column storing enum values instead of names."""

    return SAEnum(
        enum_cls,
        name=name,
        values_callable=lambda enumeration: [member.value for member in enumeration],
    )


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(UTC)


RELEASE_REQUEST_LINKS = Table(
    "release_request_links",
    Base.metadata,
    Column(
        "release_id",
        String(64),
        ForeignKey("releases.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "request_id",
        String(64),
        ForeignKey("media_requests.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class MediaRequest(Base):
    """Media request for movies or series seasons."""

    __tablename__ = "media_requests"
    __table_args__ = (
        CheckConstraint(
            "(media_type = 'movie' AND season_number IS NULL AND total_episodes IS NULL)"
            " OR media_type = 'series'",
            name="ck_media_requests_movie_series_fields",
        ),
        UniqueConstraint(
            "sonarr_series_id",
            "season_number",
            name="uq_media_requests_sonarr_series_season",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    media_type: Mapped[MediaType] = mapped_column(
        build_enum(MediaType, "media_type"),
        nullable=False,
    )
    status: Mapped[MediaRequestStatus] = mapped_column(
        build_enum(MediaRequestStatus, "media_request_status"),
        nullable=False,
        default=MediaRequestStatus.PENDING,
        server_default=MediaRequestStatus.PENDING.value,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    overview: Mapped[str | None] = mapped_column(Text())
    poster_url: Mapped[str | None] = mapped_column(String(512))
    genres: Mapped[list[str]] = mapped_column(JSONList, nullable=False, default=list)
    localizations: Mapped[dict[str, dict[str, str | None]]] = mapped_column(
        JSONDict,
        nullable=False,
        default=dict,
    )
    runtime_minutes: Mapped[int | None] = mapped_column(Integer)
    imdb_id: Mapped[str | None] = mapped_column(String(64))
    season_number: Mapped[int | None] = mapped_column(Integer)
    total_episodes: Mapped[int | None] = mapped_column(Integer)
    series_title: Mapped[str | None] = mapped_column(String(255))
    series_year: Mapped[int | None] = mapped_column(Integer)
    sonarr_series_id: Mapped[int | None] = mapped_column(Integer, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        server_default=func.now(),
        nullable=False,
    )

    releases: Mapped[list[Release]] = relationship(
        "Release",
        secondary=RELEASE_REQUEST_LINKS,
        back_populates="requests",
        lazy="selectin",
    )


class Release(Base):
    """Release tracked by the system (torrent/download)."""

    __tablename__ = "releases"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    info_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[ReleaseStatus] = mapped_column(
        build_enum(ReleaseStatus, "release_status"),
        nullable=False,
        default=ReleaseStatus.PENDING,
        server_default=ReleaseStatus.PENDING.value,
    )
    progress: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        server_default="0",
    )
    download_speed: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        server_default="0",
    )
    upload_speed: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        server_default="0",
    )
    last_exported_info_hash: Mapped[str | None] = mapped_column(String(128))
    export_failures_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    seeders: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    leechers: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    ratio: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        server_default="0",
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    torrent_source: Mapped[str | None] = mapped_column(String(255))
    quality: Mapped[str | None] = mapped_column(String(128))

    requests: Mapped[list[MediaRequest]] = relationship(
        "MediaRequest",
        secondary=RELEASE_REQUEST_LINKS,
        back_populates="releases",
        lazy="selectin",
    )
    files: Mapped[list[ReleaseFile]] = relationship(
        "ReleaseFile",
        back_populates="release",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ReleaseFile(Base):
    """Individual file within a release."""

    __tablename__ = "release_files"
    __table_args__ = (
        CheckConstraint(
            "(mapping_type != 'series') OR (season IS NOT NULL AND episode IS NOT NULL)",
            name="ck_release_files_series_mapping",
        ),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    release_id: Mapped[str] = mapped_column(
        ForeignKey("releases.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    path: Mapped[str] = mapped_column(String(1024), nullable=False)

    mapping_type: Mapped[MediaType | None] = mapped_column(
        build_enum(MediaType, "file_mapping_media_type"),
        nullable=True,
    )
    mapped_request_id: Mapped[str | None] = mapped_column(
        ForeignKey("media_requests.id", ondelete="SET NULL"),
        nullable=True,
    )
    mapped_request_title: Mapped[str | None] = mapped_column(String(255))
    season: Mapped[int | None] = mapped_column(Integer)
    episode: Mapped[int | None] = mapped_column(Integer)

    release: Mapped[Release] = relationship("Release", back_populates="files")
    mapped_request: Mapped[MediaRequest | None] = relationship("MediaRequest", lazy="selectin")


class SyncJob(Base):
    """An on-demand run of a single task.

    The API and the scheduler run as separate processes, so this table is the
    hand-off between them: the API enqueues a row and the scheduler claims it.
    Scheduled runs are not recorded here; they update :class:`ScheduledTask`.
    """

    __tablename__ = "sync_jobs"
    __table_args__ = (Index("ix_sync_jobs_status_queued_at", "status", "queued_at"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    kind: Mapped[SyncJobKind] = mapped_column(
        build_enum(SyncJobKind, "sync_job_kind"),
        nullable=False,
    )
    status: Mapped[SyncJobStatus] = mapped_column(
        build_enum(SyncJobStatus, "sync_job_status"),
        nullable=False,
        default=SyncJobStatus.QUEUED,
        server_default=SyncJobStatus.QUEUED.value,
    )
    trigger: Mapped[SyncJobTrigger] = mapped_column(
        build_enum(SyncJobTrigger, "sync_job_trigger"),
        nullable=False,
        default=SyncJobTrigger.API,
        server_default=SyncJobTrigger.API.value,
    )
    queued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text())
    result: Mapped[dict[str, object]] = mapped_column(JSONDict, nullable=False, default=dict)


class ScheduledTask(Base):
    """Last known state of a task's recurring schedule.

    Kept separate from :class:`SyncJob` so the scheduler can report when each
    task last ran without writing a history row on every tick, and so the
    schedule survives a restart.
    """

    __tablename__ = "scheduled_tasks"

    kind: Mapped[SyncJobKind] = mapped_column(
        build_enum(SyncJobKind, "scheduled_task_kind"),
        primary_key=True,
    )
    interval_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    last_execution: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_duration_ms: Mapped[int | None] = mapped_column(Integer)
    last_status: Mapped[SyncJobStatus | None] = mapped_column(
        build_enum(SyncJobStatus, "scheduled_task_status"),
        nullable=True,
    )
    last_error: Mapped[str | None] = mapped_column(Text())


__all__ = [
    "RELEASE_REQUEST_LINKS",
    "MediaRequest",
    "Release",
    "ReleaseFile",
    "ScheduledTask",
    "SyncJob",
]
