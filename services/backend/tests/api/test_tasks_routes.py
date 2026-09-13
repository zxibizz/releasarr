"""Integration tests for the task API routes."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi import status
from httpx import AsyncClient

from src.api.app import app
from src.api.routes.tasks import (
    _enqueue_use_case,
    _get_job_use_case,
    _list_jobs_use_case,
    _list_scheduled_use_case,
)
from src.application.interfaces.sync_jobs import EnqueueSyncJobResult, SyncJobRecord
from src.application.use_cases.tasks.dto import ScheduledTaskDTO
from src.application.use_cases.tasks.exceptions import SyncJobNotFoundError
from src.core.container import get_container
from src.domain.enums import SyncJobKind, SyncJobStatus, SyncJobTrigger

API_KEY_HEADER = {"X-API-Key": get_container().settings.api_key.get_secret_value()}


def make_job(
    *,
    job_id: str = "job-1",
    kind: SyncJobKind = SyncJobKind.RELEASE_SYNC,
    job_status: SyncJobStatus = SyncJobStatus.QUEUED,
    trigger: SyncJobTrigger = SyncJobTrigger.API,
) -> SyncJobRecord:
    return SyncJobRecord(
        id=job_id,
        kind=kind,
        status=job_status,
        trigger=trigger,
        queued_at=datetime(2026, 9, 12, 10, 0, tzinfo=UTC),
        started_at=None,
        finished_at=None,
        error=None,
        result={},
    )


class FakeEnqueue:
    """Returns one job per requested kind, echoing the order it was asked for."""

    def __init__(self, *, created: bool = True) -> None:
        self.created = created
        self.calls: list[tuple[tuple[SyncJobKind, ...], SyncJobTrigger]] = []

    async def execute(
        self,
        *,
        kinds: Sequence[SyncJobKind],
        trigger: SyncJobTrigger = SyncJobTrigger.API,
    ) -> list[EnqueueSyncJobResult]:
        self.calls.append((tuple(kinds), trigger))
        return [
            EnqueueSyncJobResult(
                job=make_job(job_id=f"job-{index}", kind=kind, trigger=trigger),
                created=self.created,
            )
            for index, kind in enumerate(kinds, start=1)
        ]


@contextmanager
def override_dependency(dep: Callable[..., Any], value: Any):
    app.dependency_overrides[dep] = lambda: value
    try:
        yield
    finally:
        app.dependency_overrides.pop(dep, None)


@pytest.mark.asyncio
async def test_sync_all_queues_every_task_in_order(api_client: AsyncClient) -> None:
    fake = FakeEnqueue()

    with override_dependency(_enqueue_use_case, fake):
        response = await api_client.post("/tasks/sync_all", headers=API_KEY_HEADER)

    assert response.status_code == status.HTTP_202_ACCEPTED
    assert fake.calls == [
        (
            (
                SyncJobKind.SONARR_SYNC,
                SyncJobKind.RADARR_SYNC,
                SyncJobKind.RELEASE_SYNC,
                SyncJobKind.EXPORT,
                SyncJobKind.REGRAB,
            ),
            SyncJobTrigger.API,
        )
    ]

    body = response.json()
    assert body["operation"] == "sync_all"
    assert body["status"] == "queued"
    assert body["details"]["tasks"] == [
        "sonarr_sync",
        "radarr_sync",
        "release_sync",
        "export",
        "regrab",
    ]
    # The last job finishing means the whole sequence is done.
    assert body["operation_id"] == "job-5"
    assert response.headers["Location"] == "/tasks/jobs/job-5"


@pytest.mark.asyncio
async def test_sync_downloads_queues_only_the_download_tasks(api_client: AsyncClient) -> None:
    """The download client hook skips the slow library and indexer tasks."""

    fake = FakeEnqueue()

    with override_dependency(_enqueue_use_case, fake):
        response = await api_client.post("/tasks/sync_downloads", headers=API_KEY_HEADER)

    assert response.status_code == status.HTTP_202_ACCEPTED
    assert fake.calls == [
        ((SyncJobKind.RELEASE_SYNC, SyncJobKind.EXPORT), SyncJobTrigger.DOWNLOAD_CLIENT)
    ]
    assert response.json()["operation"] == "sync_downloads"


@pytest.mark.asyncio
async def test_run_task_queues_a_single_task(api_client: AsyncClient) -> None:
    fake = FakeEnqueue()

    with override_dependency(_enqueue_use_case, fake):
        response = await api_client.post("/tasks/run/export", headers=API_KEY_HEADER)

    assert response.status_code == status.HTTP_202_ACCEPTED
    assert fake.calls == [((SyncJobKind.EXPORT,), SyncJobTrigger.API)]
    assert response.json()["operation"] == "run_export"


@pytest.mark.asyncio
async def test_run_task_rejects_an_unknown_task(api_client: AsyncClient) -> None:
    with override_dependency(_enqueue_use_case, FakeEnqueue()):
        response = await api_client.post("/tasks/run/not_a_task", headers=API_KEY_HEADER)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@pytest.mark.asyncio
async def test_reused_jobs_are_reported_as_not_created(api_client: AsyncClient) -> None:
    fake = FakeEnqueue(created=False)

    with override_dependency(_enqueue_use_case, fake):
        response = await api_client.post("/tasks/sync_all", headers=API_KEY_HEADER)

    assert response.status_code == status.HTTP_202_ACCEPTED
    body = response.json()
    assert body["details"]["created"] == 0
    assert body["message"] == "An equivalent run is already queued."


@pytest.mark.asyncio
async def test_sync_all_requires_the_api_key(api_client: AsyncClient) -> None:
    response = await api_client.post("/tasks/sync_all")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_get_sync_job_returns_the_job(api_client: AsyncClient) -> None:
    job = make_job(kind=SyncJobKind.EXPORT, job_status=SyncJobStatus.COMPLETED)
    job.started_at = datetime(2026, 9, 12, 10, 0, 1, tzinfo=UTC)
    job.finished_at = datetime(2026, 9, 12, 10, 0, 3, tzinfo=UTC)
    job.result = {"succeeded": 1, "failed": 0}

    class FakeGet:
        async def execute(self, job_id: str) -> SyncJobRecord:
            assert job_id == "job-1"
            return job

    with override_dependency(_get_job_use_case, FakeGet()):
        response = await api_client.get("/tasks/jobs/job-1", headers=API_KEY_HEADER)

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["id"] == "job-1"
    assert body["status"] == "completed"
    assert body["kind"] == "export"
    assert body["duration_ms"] == 2000
    assert body["result"] == {"succeeded": 1, "failed": 0}


@pytest.mark.asyncio
async def test_job_timestamps_are_serialized_as_utc(api_client: AsyncClient) -> None:
    """SQLite hands back naive timestamps; the browser must not read them as local."""

    job = make_job()
    job.queued_at = datetime(2026, 9, 12, 10, 0)

    class FakeGet:
        async def execute(self, job_id: str) -> SyncJobRecord:
            return job

    with override_dependency(_get_job_use_case, FakeGet()):
        response = await api_client.get("/tasks/jobs/job-1", headers=API_KEY_HEADER)

    assert response.json()["queued_at"] == "2026-09-12T10:00:00Z"


@pytest.mark.asyncio
async def test_get_sync_job_not_found_returns_404(api_client: AsyncClient) -> None:
    class FakeGet:
        async def execute(self, job_id: str) -> SyncJobRecord:
            raise SyncJobNotFoundError(job_id)

    with override_dependency(_get_job_use_case, FakeGet()):
        response = await api_client.get("/tasks/jobs/missing", headers=API_KEY_HEADER)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["code"] == "sync_job_not_found"


@pytest.mark.asyncio
async def test_list_sync_jobs_returns_jobs(api_client: AsyncClient) -> None:
    jobs = [make_job(job_id="job-2"), make_job(job_id="job-1")]

    class FakeList:
        def __init__(self) -> None:
            self.limit: int | None = None

        async def execute(self, *, limit: int = 20) -> list[SyncJobRecord]:
            self.limit = limit
            return jobs

    fake = FakeList()

    with override_dependency(_list_jobs_use_case, fake):
        response = await api_client.get(
            "/tasks/jobs",
            params={"limit": 5},
            headers=API_KEY_HEADER,
        )

    assert response.status_code == status.HTTP_200_OK
    assert fake.limit == 5
    assert [job["id"] for job in response.json()["jobs"]] == ["job-2", "job-1"]


@pytest.mark.asyncio
async def test_list_sync_jobs_rejects_an_out_of_range_limit(api_client: AsyncClient) -> None:
    class FakeList:
        async def execute(self, *, limit: int = 20) -> list[SyncJobRecord]:
            return []

    with override_dependency(_list_jobs_use_case, FakeList()):
        response = await api_client.get(
            "/tasks/jobs",
            params={"limit": 0},
            headers=API_KEY_HEADER,
        )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@pytest.mark.asyncio
async def test_list_scheduled_tasks_returns_intervals_and_next_run(
    api_client: AsyncClient,
) -> None:
    tasks = [
        ScheduledTaskDTO(
            kind=SyncJobKind.RELEASE_SYNC,
            interval_seconds=30,
            last_execution=datetime(2026, 9, 12, 10, 0, tzinfo=UTC),
            last_duration_ms=120,
            last_status=SyncJobStatus.COMPLETED,
            last_error=None,
            next_execution=datetime(2026, 9, 12, 10, 0, 30, tzinfo=UTC),
        ),
        ScheduledTaskDTO(
            kind=SyncJobKind.REGRAB,
            interval_seconds=3600,
            last_execution=None,
            last_duration_ms=None,
            last_status=None,
            last_error=None,
            next_execution=None,
        ),
    ]

    class FakeList:
        async def execute(self) -> list[ScheduledTaskDTO]:
            return tasks

    with override_dependency(_list_scheduled_use_case, FakeList()):
        response = await api_client.get("/tasks/scheduled", headers=API_KEY_HEADER)

    assert response.status_code == status.HTTP_200_OK
    body = response.json()["tasks"]
    assert [task["kind"] for task in body] == ["release_sync", "regrab"]
    assert body[0]["interval_seconds"] == 30
    assert body[0]["next_execution"] == "2026-09-12T10:00:30Z"
    assert body[1]["last_execution"] is None
    assert body[1]["next_execution"] is None
