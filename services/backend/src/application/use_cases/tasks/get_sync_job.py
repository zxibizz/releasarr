"""Read access to queued task runs and recurring task state."""

from __future__ import annotations

from datetime import UTC, timedelta

from src.application.interfaces.sync_jobs import (
    ScheduledTaskRecord,
    ScheduledTaskRepository,
    SyncJobRecord,
    SyncJobRepository,
)
from src.application.use_cases.tasks.definitions import DEFAULT_INTERVALS, TASK_ORDER
from src.application.use_cases.tasks.dto import ScheduledTaskDTO
from src.application.use_cases.tasks.exceptions import SyncJobNotFoundError


class GetSyncJobUseCase:
    """Use case returning a single task run by id."""

    def __init__(self, repository: SyncJobRepository) -> None:
        self._repository = repository

    async def execute(self, job_id: str) -> SyncJobRecord:
        job = await self._repository.get(job_id)
        if job is None:
            raise SyncJobNotFoundError(job_id)
        return job


class ListSyncJobsUseCase:
    """Use case returning the most recent task runs."""

    def __init__(self, repository: SyncJobRepository) -> None:
        self._repository = repository

    async def execute(self, *, limit: int = 20) -> list[SyncJobRecord]:
        return await self._repository.list_recent(limit=limit)


class ListScheduledTasksUseCase:
    """Use case returning every recurring task and when it next runs.

    Tasks the scheduler has not registered yet are still reported, using their
    configured interval, so the UI lists them before the worker's first run.
    """

    def __init__(self, repository: ScheduledTaskRepository) -> None:
        self._repository = repository

    async def execute(self) -> list[ScheduledTaskDTO]:
        stored = {record.kind: record for record in await self._repository.list_tasks()}
        return [self._to_dto(kind, stored.get(kind)) for kind in TASK_ORDER]

    @staticmethod
    def _to_dto(kind, record: ScheduledTaskRecord | None) -> ScheduledTaskDTO:
        interval = record.interval_seconds if record else DEFAULT_INTERVALS[kind]
        last_execution = record.last_execution if record else None

        next_execution = None
        if last_execution is not None:
            # The database may hand back naive timestamps; treat them as UTC so
            # the computed next run is comparable to anything else we emit.
            if last_execution.tzinfo is None:
                last_execution = last_execution.replace(tzinfo=UTC)
            next_execution = last_execution + timedelta(seconds=interval)

        return ScheduledTaskDTO(
            kind=kind,
            interval_seconds=interval,
            last_execution=last_execution,
            last_duration_ms=record.last_duration_ms if record else None,
            last_status=record.last_status if record else None,
            last_error=record.last_error if record else None,
            next_execution=next_execution,
        )


__all__ = ["GetSyncJobUseCase", "ListScheduledTasksUseCase", "ListSyncJobsUseCase"]
