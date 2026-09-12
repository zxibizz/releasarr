"""FastAPI routes for triggering and inspecting task runs.

These endpoints only enqueue work: the scheduler process owns execution, so the
web process never runs a task itself.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response, status

from src.api.dependencies import require_api_key
from src.api.responses import error_responses
from src.application.interfaces.sync_jobs import EnqueueSyncJobResult, SyncJobRecord
from src.application.use_cases.tasks.definitions import (
    SYNC_ALL_SEQUENCE,
    SYNC_DOWNLOADS_SEQUENCE,
)
from src.application.use_cases.tasks.dto import ScheduledTaskDTO
from src.application.use_cases.tasks.enqueue_sync import EnqueueSyncJobUseCase
from src.application.use_cases.tasks.get_sync_job import (
    GetSyncJobUseCase,
    ListScheduledTasksUseCase,
    ListSyncJobsUseCase,
)
from src.core.container import AppContainer, get_container
from src.domain.enums import SyncJobKind, SyncJobTrigger
from src.schemas.enums import AsyncJobStatus
from src.schemas.jobs import AsyncOperationResponse
from src.schemas.tasks import (
    ScheduledTask,
    ScheduledTasksResponse,
    SyncJob,
    SyncJobsResponse,
)

router = APIRouter(prefix="/tasks", tags=["Tasks"], dependencies=[Depends(require_api_key)])

_SERVER_ERROR = "Unexpected server error."

SYNC_RESPONSES = error_responses(
    {
        status.HTTP_500_INTERNAL_SERVER_ERROR: _SERVER_ERROR,
    }
)

RUN_TASK_RESPONSES = error_responses(
    {
        status.HTTP_422_UNPROCESSABLE_CONTENT: "Unknown task.",
        status.HTTP_500_INTERNAL_SERVER_ERROR: _SERVER_ERROR,
    }
)

LIST_JOBS_RESPONSES = error_responses(
    {
        status.HTTP_400_BAD_REQUEST: "Invalid pagination parameters.",
        status.HTTP_500_INTERNAL_SERVER_ERROR: _SERVER_ERROR,
    }
)

GET_JOB_RESPONSES = error_responses(
    {
        status.HTTP_404_NOT_FOUND: "Sync job not found.",
        status.HTTP_500_INTERNAL_SERVER_ERROR: _SERVER_ERROR,
    }
)

JobIdParam = Annotated[str, Path(..., alias="jobId")]
TaskKindParam = Annotated[SyncJobKind, Path(..., alias="kind")]


def _get_container() -> AppContainer:
    return get_container()


def _enqueue_use_case(
    container: AppContainer = Depends(_get_container),
) -> EnqueueSyncJobUseCase:
    return container.use_cases.tasks.enqueue_sync


def _get_job_use_case(container: AppContainer = Depends(_get_container)) -> GetSyncJobUseCase:
    return container.use_cases.tasks.get_sync_job


def _list_jobs_use_case(container: AppContainer = Depends(_get_container)) -> ListSyncJobsUseCase:
    return container.use_cases.tasks.list_sync_jobs


def _list_scheduled_use_case(
    container: AppContainer = Depends(_get_container),
) -> ListScheduledTasksUseCase:
    return container.use_cases.tasks.list_scheduled_tasks


def _job_location(job_id: str) -> str:
    return f"/tasks/jobs/{job_id}"


def _record_to_job(record: SyncJobRecord) -> SyncJob:
    return SyncJob(
        id=record.id,
        kind=record.kind,
        status=record.status,
        trigger=record.trigger,
        queued_at=record.queued_at,
        started_at=record.started_at,
        finished_at=record.finished_at,
        duration_ms=record.duration_ms,
        error=record.error,
        result=record.result or None,
    )


def _dto_to_scheduled_task(dto: ScheduledTaskDTO) -> ScheduledTask:
    return ScheduledTask(
        kind=dto.kind,
        interval_seconds=dto.interval_seconds,
        last_execution=dto.last_execution,
        last_duration_ms=dto.last_duration_ms,
        last_status=dto.last_status,
        last_error=dto.last_error,
        next_execution=dto.next_execution,
    )


def _enqueue_to_response(
    results: Sequence[EnqueueSyncJobResult],
    *,
    operation: str,
    queued_message: str,
) -> AsyncOperationResponse:
    """Summarize an enqueue as a single operation the caller can poll.

    A request may queue several tasks; the last one finishing means the whole
    sequence is done, so that job is the one worth tracking.
    """

    tracked = results[-1]
    created = [result for result in results if result.created]
    message = queued_message if created else "An equivalent run is already queued."

    return AsyncOperationResponse(
        operation=operation,
        status=AsyncJobStatus.QUEUED,
        operation_id=tracked.job.id,
        location=_job_location(tracked.job.id),
        message=message,
        resource_id=tracked.job.id,
        details={
            "job_ids": [result.job.id for result in results],
            "tasks": [result.job.kind.value for result in results],
            "created": len(created),
        },
    )


async def _queue(
    *,
    kinds: Sequence[SyncJobKind],
    trigger: SyncJobTrigger,
    operation: str,
    queued_message: str,
    use_case: EnqueueSyncJobUseCase,
    response: Response,
) -> AsyncOperationResponse:
    results = await use_case.execute(kinds=kinds, trigger=trigger)
    payload = _enqueue_to_response(
        results,
        operation=operation,
        queued_message=queued_message,
    )
    if payload.location:
        response.headers["Location"] = payload.location
    return payload


@router.post(
    "/sync_all",
    response_model=AsyncOperationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses=SYNC_RESPONSES,
    summary="Queue every task",
)
async def trigger_full_sync(
    response: Response,
    enqueue_use_case: EnqueueSyncJobUseCase = Depends(_enqueue_use_case),
) -> AsyncOperationResponse:
    return await _queue(
        kinds=SYNC_ALL_SEQUENCE,
        trigger=SyncJobTrigger.API,
        operation="sync_all",
        queued_message="Full sync queued.",
        use_case=enqueue_use_case,
        response=response,
    )


@router.post(
    "/sync_downloads",
    response_model=AsyncOperationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses=SYNC_RESPONSES,
    summary="Queue a download sync and Sonarr import",
)
async def trigger_download_sync(
    response: Response,
    enqueue_use_case: EnqueueSyncJobUseCase = Depends(_enqueue_use_case),
) -> AsyncOperationResponse:
    """Entry point for a download client reporting that a torrent finished."""

    return await _queue(
        kinds=SYNC_DOWNLOADS_SEQUENCE,
        trigger=SyncJobTrigger.DOWNLOAD_CLIENT,
        operation="sync_downloads",
        queued_message="Download sync queued.",
        use_case=enqueue_use_case,
        response=response,
    )


@router.post(
    "/run/{kind}",
    response_model=AsyncOperationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses=RUN_TASK_RESPONSES,
    summary="Queue a single task",
)
async def run_task(
    kind: TaskKindParam,
    response: Response,
    enqueue_use_case: EnqueueSyncJobUseCase = Depends(_enqueue_use_case),
) -> AsyncOperationResponse:
    return await _queue(
        kinds=[kind],
        trigger=SyncJobTrigger.API,
        operation=f"run_{kind.value}",
        queued_message="Task queued.",
        use_case=enqueue_use_case,
        response=response,
    )


@router.get(
    "/scheduled",
    response_model=ScheduledTasksResponse,
    responses=SYNC_RESPONSES,
    summary="List recurring tasks",
)
async def list_scheduled_tasks(
    list_use_case: ListScheduledTasksUseCase = Depends(_list_scheduled_use_case),
) -> ScheduledTasksResponse:
    tasks = await list_use_case.execute()
    return ScheduledTasksResponse(tasks=[_dto_to_scheduled_task(task) for task in tasks])


@router.get(
    "/jobs",
    response_model=SyncJobsResponse,
    responses=LIST_JOBS_RESPONSES,
    summary="List recent task runs",
)
async def list_sync_jobs(
    limit: int = Query(default=20, ge=1, le=100),
    list_use_case: ListSyncJobsUseCase = Depends(_list_jobs_use_case),
) -> SyncJobsResponse:
    records = await list_use_case.execute(limit=limit)
    return SyncJobsResponse(jobs=[_record_to_job(record) for record in records])


@router.get(
    "/jobs/{jobId}",
    response_model=SyncJob,
    responses=GET_JOB_RESPONSES,
    summary="Get a task run",
)
async def get_sync_job(
    job_id: JobIdParam,
    get_use_case: GetSyncJobUseCase = Depends(_get_job_use_case),
) -> SyncJob:
    record = await get_use_case.execute(job_id)
    return _record_to_job(record)


__all__ = ["router"]
