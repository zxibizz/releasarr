"""Tests for the SQLAlchemy task repositories."""

from __future__ import annotations

import pytest

from src.db.session import DBManager
from src.domain.enums import SyncJobKind, SyncJobStatus, SyncJobTrigger
from src.infrastructure.sync_jobs import (
    SqlAlchemyScheduledTaskRepository,
    SqlAlchemySyncJobRepository,
)

EXPORT = SyncJobKind.EXPORT
RELEASE_SYNC = SyncJobKind.RELEASE_SYNC
REGRAB = SyncJobKind.REGRAB


@pytest.fixture()
def repository(db_manager: DBManager) -> SqlAlchemySyncJobRepository:
    return SqlAlchemySyncJobRepository(db=db_manager)


@pytest.fixture()
def scheduled(db_manager: DBManager) -> SqlAlchemyScheduledTaskRepository:
    return SqlAlchemyScheduledTaskRepository(db=db_manager)


async def test_enqueue_creates_a_queued_job(repository: SqlAlchemySyncJobRepository) -> None:
    result = await repository.enqueue(kind=EXPORT, trigger=SyncJobTrigger.API)

    assert result.created is True
    assert result.job.status == SyncJobStatus.QUEUED
    assert result.job.kind == EXPORT
    assert result.job.trigger == SyncJobTrigger.API
    assert result.job.started_at is None


async def test_enqueue_collapses_onto_an_already_queued_job(
    repository: SqlAlchemySyncJobRepository,
) -> None:
    """A burst of finished torrents must not queue a run each."""

    first = await repository.enqueue(kind=RELEASE_SYNC, trigger=SyncJobTrigger.DOWNLOAD_CLIENT)
    second = await repository.enqueue(kind=RELEASE_SYNC, trigger=SyncJobTrigger.DOWNLOAD_CLIENT)

    assert second.created is False
    assert second.job.id == first.job.id
    assert len(await repository.list_recent()) == 1


async def test_enqueue_keeps_distinct_kinds_apart(
    repository: SqlAlchemySyncJobRepository,
) -> None:
    release_sync = await repository.enqueue(kind=RELEASE_SYNC, trigger=SyncJobTrigger.API)
    export = await repository.enqueue(kind=EXPORT, trigger=SyncJobTrigger.API)

    assert export.created is True
    assert export.job.id != release_sync.job.id


async def test_enqueue_sequence_queues_tasks_in_order(
    repository: SqlAlchemySyncJobRepository,
) -> None:
    results = await repository.enqueue_sequence(
        kinds=[RELEASE_SYNC, EXPORT],
        trigger=SyncJobTrigger.DOWNLOAD_CLIENT,
    )

    assert [result.job.kind for result in results] == [RELEASE_SYNC, EXPORT]

    first = await repository.claim_next()
    second = await repository.claim_next()
    assert first is not None and second is not None
    assert first.kind == RELEASE_SYNC
    assert second.kind == EXPORT


async def test_enqueue_sequence_does_not_reuse_a_job_that_runs_too_early(
    repository: SqlAlchemySyncJobRepository,
) -> None:
    """An export must never be scheduled ahead of the sync that feeds it."""

    early_export = await repository.enqueue(kind=EXPORT, trigger=SyncJobTrigger.API)

    results = await repository.enqueue_sequence(
        kinds=[RELEASE_SYNC, EXPORT],
        trigger=SyncJobTrigger.DOWNLOAD_CLIENT,
    )

    assert results[1].created is True
    assert results[1].job.id != early_export.job.id

    order = [
        (await repository.claim_next()),
        (await repository.claim_next()),
        (await repository.claim_next()),
    ]
    assert [job.kind for job in order if job] == [EXPORT, RELEASE_SYNC, EXPORT]


async def test_enqueue_sequence_reuses_jobs_already_queued_in_order(
    repository: SqlAlchemySyncJobRepository,
) -> None:
    first = await repository.enqueue_sequence(
        kinds=[RELEASE_SYNC, EXPORT],
        trigger=SyncJobTrigger.DOWNLOAD_CLIENT,
    )
    second = await repository.enqueue_sequence(
        kinds=[RELEASE_SYNC, EXPORT],
        trigger=SyncJobTrigger.DOWNLOAD_CLIENT,
    )

    assert [result.created for result in second] == [False, False]
    assert [result.job.id for result in second] == [result.job.id for result in first]


async def test_enqueue_after_claim_creates_a_new_job(
    repository: SqlAlchemySyncJobRepository,
) -> None:
    """Work that arrives mid-run needs its own job rather than joining the running one."""

    first = await repository.enqueue(kind=RELEASE_SYNC, trigger=SyncJobTrigger.API)
    await repository.claim_next()

    second = await repository.enqueue(kind=RELEASE_SYNC, trigger=SyncJobTrigger.API)

    assert second.created is True
    assert second.job.id != first.job.id


async def test_claim_next_takes_the_oldest_job(repository: SqlAlchemySyncJobRepository) -> None:
    first = await repository.enqueue(kind=RELEASE_SYNC, trigger=SyncJobTrigger.API)
    await repository.claim_next()
    second = await repository.enqueue(kind=RELEASE_SYNC, trigger=SyncJobTrigger.API)

    claimed = await repository.claim_next()

    assert claimed is not None
    assert claimed.id == second.job.id
    assert claimed.id != first.job.id
    assert claimed.status == SyncJobStatus.RUNNING
    assert claimed.started_at is not None


async def test_claim_next_returns_none_when_queue_is_empty(
    repository: SqlAlchemySyncJobRepository,
) -> None:
    assert await repository.claim_next() is None


async def test_finish_records_the_result(repository: SqlAlchemySyncJobRepository) -> None:
    queued = await repository.enqueue(kind=EXPORT, trigger=SyncJobTrigger.API)
    await repository.claim_next()

    await repository.finish(
        queued.job.id,
        status=SyncJobStatus.COMPLETED,
        result={"succeeded": 2, "failed": 0},
    )

    job = await repository.get(queued.job.id)
    assert job is not None
    assert job.status == SyncJobStatus.COMPLETED
    assert job.finished_at is not None
    assert job.error is None
    assert job.result == {"succeeded": 2, "failed": 0}
    assert job.duration_ms is not None


async def test_finish_records_the_error(repository: SqlAlchemySyncJobRepository) -> None:
    queued = await repository.enqueue(kind=EXPORT, trigger=SyncJobTrigger.API)
    await repository.claim_next()

    await repository.finish(
        queued.job.id,
        status=SyncJobStatus.FAILED,
        result={},
        error="boom",
    )

    job = await repository.get(queued.job.id)
    assert job is not None
    assert job.status == SyncJobStatus.FAILED
    assert job.error == "boom"


async def test_get_returns_none_for_unknown_job(
    repository: SqlAlchemySyncJobRepository,
) -> None:
    assert await repository.get("missing") is None


async def test_list_recent_returns_newest_first(
    repository: SqlAlchemySyncJobRepository,
) -> None:
    first = await repository.enqueue(kind=RELEASE_SYNC, trigger=SyncJobTrigger.API)
    await repository.claim_next()
    second = await repository.enqueue(kind=EXPORT, trigger=SyncJobTrigger.API)

    jobs = await repository.list_recent(limit=10)

    assert [job.id for job in jobs] == [second.job.id, first.job.id]


async def test_fail_running_clears_jobs_left_by_a_dead_worker(
    repository: SqlAlchemySyncJobRepository,
) -> None:
    queued = await repository.enqueue(kind=EXPORT, trigger=SyncJobTrigger.API)
    await repository.claim_next()

    failed = await repository.fail_running(error="Scheduler restarted")

    assert failed == 1
    job = await repository.get(queued.job.id)
    assert job is not None
    assert job.status == SyncJobStatus.FAILED
    assert job.error == "Scheduler restarted"


async def test_fail_running_leaves_queued_jobs_alone(
    repository: SqlAlchemySyncJobRepository,
) -> None:
    queued = await repository.enqueue(kind=EXPORT, trigger=SyncJobTrigger.API)

    assert await repository.fail_running(error="Scheduler restarted") == 0

    job = await repository.get(queued.job.id)
    assert job is not None
    assert job.status == SyncJobStatus.QUEUED


async def test_prune_keeps_the_newest_finished_jobs(
    repository: SqlAlchemySyncJobRepository,
) -> None:
    finished = []
    for _ in range(3):
        queued = await repository.enqueue(kind=EXPORT, trigger=SyncJobTrigger.API)
        await repository.claim_next()
        await repository.finish(queued.job.id, status=SyncJobStatus.COMPLETED)
        finished.append(queued.job.id)

    removed = await repository.prune(keep=1)

    assert removed == 2
    remaining = [job.id for job in await repository.list_recent()]
    assert remaining == [finished[-1]]


async def test_prune_never_drops_pending_work(
    repository: SqlAlchemySyncJobRepository,
) -> None:
    done = await repository.enqueue(kind=EXPORT, trigger=SyncJobTrigger.API)
    await repository.claim_next()
    await repository.finish(done.job.id, status=SyncJobStatus.COMPLETED)

    waiting = await repository.enqueue(kind=REGRAB, trigger=SyncJobTrigger.API)

    await repository.prune(keep=0)

    remaining = [job.id for job in await repository.list_recent()]
    assert remaining == [waiting.job.id]


async def test_register_is_idempotent_and_refreshes_the_interval(
    scheduled: SqlAlchemyScheduledTaskRepository,
) -> None:
    await scheduled.register(kind=RELEASE_SYNC, interval_seconds=30)
    updated = await scheduled.register(kind=RELEASE_SYNC, interval_seconds=45)

    assert updated.interval_seconds == 45
    assert len(await scheduled.list_tasks()) == 1


async def test_record_run_stores_the_outcome(
    scheduled: SqlAlchemyScheduledTaskRepository,
) -> None:
    await scheduled.register(kind=EXPORT, interval_seconds=300)

    await scheduled.record_run(
        EXPORT,
        status=SyncJobStatus.FAILED,
        duration_ms=1234,
        error="sonarr unreachable",
    )

    task = await scheduled.get(EXPORT)
    assert task is not None
    assert task.last_execution is not None
    assert task.last_duration_ms == 1234
    assert task.last_status == SyncJobStatus.FAILED
    assert task.last_error == "sonarr unreachable"


async def test_record_run_ignores_an_unregistered_task(
    scheduled: SqlAlchemyScheduledTaskRepository,
) -> None:
    await scheduled.record_run(REGRAB, status=SyncJobStatus.COMPLETED, duration_ms=10)

    assert await scheduled.get(REGRAB) is None
