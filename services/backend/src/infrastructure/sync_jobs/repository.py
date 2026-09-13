"""SQLAlchemy-backed implementations of the task repository protocols."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.sync_jobs import (
    EnqueueSyncJobResult,
    ScheduledTaskRecord,
    ScheduledTaskRepository,
    SyncJobRecord,
    SyncJobRepository,
)
from src.db.repository import BaseSqlAlchemyRepository
from src.domain import models
from src.domain.enums import SyncJobKind, SyncJobStatus, SyncJobTrigger
from src.domain.models import utc_now

_TERMINAL_STATUSES = (SyncJobStatus.COMPLETED, SyncJobStatus.FAILED)


@dataclass(slots=True)
class SqlAlchemySyncJobRepository(BaseSqlAlchemyRepository, SyncJobRepository):
    """Repository persisting on-demand task runs using SQLAlchemy sessions."""

    async def enqueue(
        self,
        *,
        kind: SyncJobKind,
        trigger: SyncJobTrigger,
    ) -> EnqueueSyncJobResult:
        results = await self.enqueue_sequence(kinds=[kind], trigger=trigger)
        return results[0]

    async def enqueue_sequence(
        self,
        *,
        kinds: Sequence[SyncJobKind],
        trigger: SyncJobTrigger,
    ) -> list[EnqueueSyncJobResult]:
        results: list[EnqueueSyncJobResult] = []

        async with self.db.transaction() as session:
            # Tracks where the previous task in the sequence sits in the queue, so
            # a reused job can never end up scheduled ahead of its predecessor.
            after: datetime | None = None

            for kind in kinds:
                pending = await self._find_queued(session, kind, after=after)
                if pending is not None:
                    results.append(
                        EnqueueSyncJobResult(job=self._to_record(pending), created=False)
                    )
                    after = pending.queued_at
                    continue

                job = models.SyncJob(
                    id=uuid4().hex,
                    kind=kind,
                    status=SyncJobStatus.QUEUED,
                    trigger=trigger,
                    queued_at=utc_now(),
                    result={},
                )
                session.add(job)
                await session.flush()
                results.append(EnqueueSyncJobResult(job=self._to_record(job), created=True))
                after = job.queued_at

        return results

    @staticmethod
    async def _find_queued(
        session: AsyncSession,
        kind: SyncJobKind,
        *,
        after: datetime | None,
    ) -> models.SyncJob | None:
        """Oldest queued job of ``kind`` that would still run after ``after``."""

        stmt = select(models.SyncJob).where(
            models.SyncJob.status == SyncJobStatus.QUEUED,
            models.SyncJob.kind == kind,
        )
        if after is not None:
            stmt = stmt.where(models.SyncJob.queued_at >= after)

        result = await session.execute(stmt.order_by(models.SyncJob.queued_at.asc()).limit(1))
        return result.scalar_one_or_none()

    async def claim_next(self) -> SyncJobRecord | None:
        async with self.db.transaction() as session:
            result = await session.execute(
                select(models.SyncJob)
                .where(models.SyncJob.status == SyncJobStatus.QUEUED)
                .order_by(models.SyncJob.queued_at.asc())
                .limit(1)
                .with_for_update()
            )
            job = result.scalar_one_or_none()
            if job is None:
                return None

            job.status = SyncJobStatus.RUNNING
            job.started_at = utc_now()
            await session.flush()
            return self._to_record(job)

    async def finish(
        self,
        job_id: str,
        *,
        status: SyncJobStatus,
        result: dict[str, object] | None = None,
        error: str | None = None,
    ) -> None:
        async with self.db.transaction() as session:
            job = await session.get(models.SyncJob, job_id)
            if job is None:
                return

            job.status = status
            job.finished_at = utc_now()
            job.result = result or {}
            job.error = error
            await session.flush()

    async def get(self, job_id: str) -> SyncJobRecord | None:
        async with self.db.session() as session:
            job = await session.get(models.SyncJob, job_id)
            return None if job is None else self._to_record(job)

    async def list_recent(self, *, limit: int = 20) -> list[SyncJobRecord]:
        async with self.db.session() as session:
            result = await session.execute(
                select(models.SyncJob).order_by(models.SyncJob.queued_at.desc()).limit(limit)
            )
            return [self._to_record(job) for job in result.scalars().all()]

    async def fail_running(self, *, error: str) -> int:
        async with self.db.transaction() as session:
            result = await session.execute(
                update(models.SyncJob)
                .where(models.SyncJob.status == SyncJobStatus.RUNNING)
                .values(
                    status=SyncJobStatus.FAILED,
                    finished_at=utc_now(),
                    error=error,
                )
            )
            return int(result.rowcount or 0)

    async def prune(self, *, keep: int) -> int:
        """Trim finished history, leaving queued and running jobs untouched."""

        async with self.db.transaction() as session:
            survivors = (
                select(models.SyncJob.id)
                .where(models.SyncJob.status.in_(_TERMINAL_STATUSES))
                .order_by(models.SyncJob.queued_at.desc())
                .limit(keep)
                .scalar_subquery()
            )
            result = await session.execute(
                delete(models.SyncJob).where(
                    models.SyncJob.status.in_(_TERMINAL_STATUSES),
                    models.SyncJob.id.not_in(survivors),
                )
            )
            return int(result.rowcount or 0)

    @staticmethod
    def _to_record(job: models.SyncJob) -> SyncJobRecord:
        return SyncJobRecord(
            id=job.id,
            kind=job.kind,
            status=job.status,
            trigger=job.trigger,
            queued_at=job.queued_at,
            started_at=job.started_at,
            finished_at=job.finished_at,
            error=job.error,
            result=dict(job.result or {}),
        )


@dataclass(slots=True)
class SqlAlchemyScheduledTaskRepository(BaseSqlAlchemyRepository, ScheduledTaskRepository):
    """Repository persisting recurring task state using SQLAlchemy sessions."""

    async def list_tasks(self) -> list[ScheduledTaskRecord]:
        async with self.db.session() as session:
            result = await session.execute(select(models.ScheduledTask))
            return [self._to_record(task) for task in result.scalars().all()]

    async def get(self, kind: SyncJobKind) -> ScheduledTaskRecord | None:
        async with self.db.session() as session:
            task = await session.get(models.ScheduledTask, kind)
            return None if task is None else self._to_record(task)

    async def register(self, *, kind: SyncJobKind, interval_seconds: int) -> ScheduledTaskRecord:
        async with self.db.transaction() as session:
            task = await session.get(models.ScheduledTask, kind)
            if task is None:
                task = models.ScheduledTask(kind=kind, interval_seconds=interval_seconds)
                session.add(task)
            else:
                task.interval_seconds = interval_seconds
            await session.flush()
            return self._to_record(task)

    async def record_run(
        self,
        kind: SyncJobKind,
        *,
        status: SyncJobStatus,
        duration_ms: int,
        error: str | None = None,
        executed_at: datetime | None = None,
    ) -> None:
        async with self.db.transaction() as session:
            task = await session.get(models.ScheduledTask, kind)
            if task is None:
                return

            task.last_execution = executed_at or utc_now()
            task.last_duration_ms = duration_ms
            task.last_status = status
            task.last_error = error
            await session.flush()

    @staticmethod
    def _to_record(task: models.ScheduledTask) -> ScheduledTaskRecord:
        return ScheduledTaskRecord(
            kind=task.kind,
            interval_seconds=task.interval_seconds,
            last_execution=task.last_execution,
            last_duration_ms=task.last_duration_ms,
            last_status=task.last_status,
            last_error=task.last_error,
        )


__all__ = ["SqlAlchemyScheduledTaskRepository", "SqlAlchemySyncJobRepository"]
