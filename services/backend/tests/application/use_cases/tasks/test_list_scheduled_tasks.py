"""Tests for the scheduled task listing use case."""

from __future__ import annotations

from datetime import UTC, datetime

from src.application.interfaces.sync_jobs import ScheduledTaskRecord
from src.application.use_cases.tasks.definitions import DEFAULT_INTERVALS, TASK_ORDER
from src.application.use_cases.tasks.get_sync_job import ListScheduledTasksUseCase
from src.domain.enums import SyncJobKind, SyncJobStatus


class FakeRepository:
    def __init__(self, records: list[ScheduledTaskRecord]) -> None:
        self._records = records

    async def list_tasks(self) -> list[ScheduledTaskRecord]:
        return self._records


async def test_every_task_is_listed_in_order_even_when_never_run() -> None:
    """The page must list the full task set before the scheduler's first run."""

    use_case = ListScheduledTasksUseCase(repository=FakeRepository([]))

    tasks = await use_case.execute()

    assert [task.kind for task in tasks] == list(TASK_ORDER)
    assert all(task.last_execution is None for task in tasks)
    assert all(task.next_execution is None for task in tasks)
    assert [task.interval_seconds for task in tasks] == [
        DEFAULT_INTERVALS[kind] for kind in TASK_ORDER
    ]


async def test_next_execution_is_derived_from_the_last_run() -> None:
    record = ScheduledTaskRecord(
        kind=SyncJobKind.EXPORT,
        interval_seconds=300,
        last_execution=datetime(2026, 9, 12, 10, 0, tzinfo=UTC),
        last_duration_ms=250,
        last_status=SyncJobStatus.COMPLETED,
        last_error=None,
    )
    use_case = ListScheduledTasksUseCase(repository=FakeRepository([record]))

    export = next(task for task in await use_case.execute() if task.kind is SyncJobKind.EXPORT)

    assert export.next_execution == datetime(2026, 9, 12, 10, 5, tzinfo=UTC)
    assert export.last_duration_ms == 250
    assert export.last_status is SyncJobStatus.COMPLETED


async def test_naive_timestamps_are_treated_as_utc() -> None:
    """SQLite drops the timezone, so a naive value must not shift the next run."""

    record = ScheduledTaskRecord(
        kind=SyncJobKind.REGRAB,
        interval_seconds=3600,
        last_execution=datetime(2026, 9, 12, 10, 0),
        last_duration_ms=None,
        last_status=None,
        last_error=None,
    )
    use_case = ListScheduledTasksUseCase(repository=FakeRepository([record]))

    regrab = next(task for task in await use_case.execute() if task.kind is SyncJobKind.REGRAB)

    assert regrab.last_execution == datetime(2026, 9, 12, 10, 0, tzinfo=UTC)
    assert regrab.next_execution == datetime(2026, 9, 12, 11, 0, tzinfo=UTC)


async def test_stored_interval_overrides_the_default() -> None:
    """A task registered with an older interval reports what the scheduler used."""

    record = ScheduledTaskRecord(
        kind=SyncJobKind.RELEASE_SYNC,
        interval_seconds=90,
        last_execution=None,
        last_duration_ms=None,
        last_status=None,
        last_error=None,
    )
    use_case = ListScheduledTasksUseCase(repository=FakeRepository([record]))

    release_sync = next(
        task for task in await use_case.execute() if task.kind is SyncJobKind.RELEASE_SYNC
    )

    assert release_sync.interval_seconds == 90
