"""Schemas for the task endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import field_serializer

from src.schemas.base import APIModel
from src.schemas.enums import SyncJobKind, SyncJobStatus, SyncJobTrigger


def _as_utc_iso(value: datetime | None) -> str | None:
    """Render a timestamp as UTC ISO-8601, assuming UTC for naive values.

    SQLite drops timezone information, so timestamps read back from the database
    are naive even though they were stored as UTC.
    """

    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


class SyncJob(APIModel):
    id: str
    kind: SyncJobKind
    status: SyncJobStatus
    trigger: SyncJobTrigger
    queued_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int | None = None
    error: str | None = None
    result: dict[str, Any] | None = None

    @field_serializer("queued_at", "started_at", "finished_at")
    def _serialize_datetime(self, value: datetime | None) -> str | None:
        return _as_utc_iso(value)


class SyncJobsResponse(APIModel):
    jobs: list[SyncJob]


class ScheduledTask(APIModel):
    kind: SyncJobKind
    interval_seconds: int
    last_execution: datetime | None = None
    last_duration_ms: int | None = None
    last_status: SyncJobStatus | None = None
    last_error: str | None = None
    next_execution: datetime | None = None

    @field_serializer("last_execution", "next_execution")
    def _serialize_datetime(self, value: datetime | None) -> str | None:
        return _as_utc_iso(value)


class ScheduledTasksResponse(APIModel):
    tasks: list[ScheduledTask]


__all__ = ["ScheduledTask", "ScheduledTasksResponse", "SyncJob", "SyncJobsResponse"]
