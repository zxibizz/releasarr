"""Interfaces supporting the task hand-off between API and scheduler."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from src.domain.enums import SyncJobKind, SyncJobStatus, SyncJobTrigger


@dataclass(slots=True)
class SyncJobRecord:
    """Normalized representation of a queued or finished task run."""

    id: str
    kind: SyncJobKind
    status: SyncJobStatus
    trigger: SyncJobTrigger
    queued_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    error: str | None
    result: dict[str, object]

    @property
    def duration_ms(self) -> int | None:
        """Wall-clock run time, or None while the job has not finished."""

        if self.started_at is None or self.finished_at is None:
            return None
        return int((self.finished_at - self.started_at).total_seconds() * 1000)


@dataclass(slots=True)
class EnqueueSyncJobResult:
    """Outcome of an enqueue attempt.

    ``created`` is False when an equivalent job was already waiting, in which
    case ``job`` is that pre-existing job.
    """

    job: SyncJobRecord
    created: bool


@dataclass(slots=True)
class ScheduledTaskRecord:
    """Last known state of a task's recurring schedule."""

    kind: SyncJobKind
    interval_seconds: int
    last_execution: datetime | None
    last_duration_ms: int | None
    last_status: SyncJobStatus | None
    last_error: str | None


class SyncJobRepository(Protocol):
    """Persistence boundary for on-demand task runs."""

    async def enqueue(
        self,
        *,
        kind: SyncJobKind,
        trigger: SyncJobTrigger,
    ) -> EnqueueSyncJobResult:
        """Queue a task unless an equivalent one is already waiting."""

    async def enqueue_sequence(
        self,
        *,
        kinds: Sequence[SyncJobKind],
        trigger: SyncJobTrigger,
    ) -> list[EnqueueSyncJobResult]:
        """Queue several tasks, preserving the order they were requested in."""

    async def claim_next(self) -> SyncJobRecord | None:
        """Atomically take the oldest queued job and mark it running."""

    async def finish(
        self,
        job_id: str,
        *,
        status: SyncJobStatus,
        result: dict[str, object] | None = None,
        error: str | None = None,
    ) -> None:
        """Record the terminal state of a claimed job."""

    async def get(self, job_id: str) -> SyncJobRecord | None:
        """Return a single job, or None when it does not exist."""

    async def list_recent(self, *, limit: int = 20) -> list[SyncJobRecord]:
        """Return the most recently queued jobs, newest first."""

    async def fail_running(self, *, error: str) -> int:
        """Fail jobs left running by a previous process and return the count."""

    async def prune(self, *, keep: int) -> int:
        """Drop all but the newest ``keep`` finished jobs and return the count."""


class ScheduledTaskRepository(Protocol):
    """Persistence boundary for recurring task state."""

    async def list_tasks(self) -> list[ScheduledTaskRecord]:
        """Return every known scheduled task."""

    async def get(self, kind: SyncJobKind) -> ScheduledTaskRecord | None:
        """Return one scheduled task, or None when it has never been recorded."""

    async def register(self, *, kind: SyncJobKind, interval_seconds: int) -> ScheduledTaskRecord:
        """Ensure a task row exists and its interval is current."""

    async def record_run(
        self,
        kind: SyncJobKind,
        *,
        status: SyncJobStatus,
        duration_ms: int,
        error: str | None = None,
        executed_at: datetime | None = None,
    ) -> None:
        """Store the outcome of a scheduled run."""


__all__ = [
    "EnqueueSyncJobResult",
    "ScheduledTaskRecord",
    "ScheduledTaskRepository",
    "SyncJobRecord",
    "SyncJobRepository",
]
