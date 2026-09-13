"""Tests for the on-demand task runner."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import cast

import pytest

from src.db.session import DBManager
from src.domain.enums import SyncJobKind, SyncJobStatus, SyncJobTrigger
from src.infrastructure.sync_jobs import SqlAlchemySyncJobRepository
from src.tasks.sync_jobs import SyncJobRunner
from src.tasks.sync_steps import StepSummary, SyncSteps


class FakeSteps:
    """Records which steps ran, and optionally fails some of them."""

    def __init__(self, failing: set[str] | None = None) -> None:
        self.calls: list[str] = []
        self._failing = failing or set()

    def for_kind(self, kind: SyncJobKind) -> Callable[[], Awaitable[StepSummary]]:
        async def run() -> StepSummary:
            self.calls.append(kind.value)
            if kind.value in self._failing:
                raise RuntimeError(f"{kind.value} exploded")
            return {"ran": kind.value}

        return run


@pytest.fixture()
def repository(db_manager: DBManager) -> SqlAlchemySyncJobRepository:
    return SqlAlchemySyncJobRepository(db=db_manager)


def make_runner(
    repository: SqlAlchemySyncJobRepository,
    steps: FakeSteps,
) -> SyncJobRunner:
    return SyncJobRunner(repository=repository, steps=cast(SyncSteps, steps))


async def test_run_next_returns_none_when_queue_is_empty(
    repository: SqlAlchemySyncJobRepository,
) -> None:
    steps = FakeSteps()

    assert await make_runner(repository, steps).run_next() is None
    assert steps.calls == []


async def test_run_next_runs_the_task_the_job_names(
    repository: SqlAlchemySyncJobRepository,
) -> None:
    queued = await repository.enqueue(
        kind=SyncJobKind.EXPORT,
        trigger=SyncJobTrigger.DOWNLOAD_CLIENT,
    )
    steps = FakeSteps()

    await make_runner(repository, steps).run_next()

    assert steps.calls == ["export"]
    job = await repository.get(queued.job.id)
    assert job is not None
    assert job.status == SyncJobStatus.COMPLETED
    assert job.result == {"ran": "export"}


async def test_a_failing_task_is_recorded_as_failed(
    repository: SqlAlchemySyncJobRepository,
) -> None:
    queued = await repository.enqueue(
        kind=SyncJobKind.SONARR_SYNC,
        trigger=SyncJobTrigger.API,
    )
    steps = FakeSteps(failing={"sonarr_sync"})

    await make_runner(repository, steps).run_next()

    job = await repository.get(queued.job.id)
    assert job is not None
    assert job.status == SyncJobStatus.FAILED
    assert job.error == "sonarr_sync exploded"
    assert job.result == {"error": "sonarr_sync exploded"}


async def test_a_failing_task_does_not_block_the_rest_of_the_queue(
    repository: SqlAlchemySyncJobRepository,
) -> None:
    await repository.enqueue_sequence(
        kinds=[SyncJobKind.RELEASE_SYNC, SyncJobKind.EXPORT],
        trigger=SyncJobTrigger.DOWNLOAD_CLIENT,
    )
    steps = FakeSteps(failing={"release_sync"})
    runner = make_runner(repository, steps)

    assert await runner.run_next() is not None
    assert await runner.run_next() is not None

    assert steps.calls == ["release_sync", "export"]
    statuses = [job.status for job in await repository.list_recent()]
    assert statuses == [SyncJobStatus.COMPLETED, SyncJobStatus.FAILED]


async def test_run_next_drains_one_job_per_call(
    repository: SqlAlchemySyncJobRepository,
) -> None:
    await repository.enqueue(kind=SyncJobKind.REGRAB, trigger=SyncJobTrigger.API)
    steps = FakeSteps()
    runner = make_runner(repository, steps)

    assert await runner.run_next() is not None
    assert await runner.run_next() is None
    assert steps.calls == ["regrab"]
