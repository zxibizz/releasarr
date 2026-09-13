"""FastAPI routes for inspecting and testing the configured indexers."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from src.api.dependencies import require_api_key
from src.api.responses import error_responses
from src.application.use_cases.indexers.dto import (
    IndexerDTO,
    IndexerHistoryPageDTO,
    IndexerLogsPageDTO,
    IndexerTestResultDTO,
)
from src.application.use_cases.indexers.list_history import ListIndexerHistoryUseCase
from src.application.use_cases.indexers.list_indexers import ListIndexersUseCase
from src.application.use_cases.indexers.list_logs import ListIndexerLogsUseCase
from src.application.use_cases.indexers.run_indexer_tests import (
    RunAllIndexerTestsUseCase,
    RunIndexerTestUseCase,
)
from src.core.container import AppContainer, get_container
from src.schemas.enums import IndexerEventType, IndexerLogLevel
from src.schemas.indexers import (
    Indexer,
    IndexerHistoryEntry,
    IndexerHistoryResponse,
    IndexerLogEntry,
    IndexerLogsResponse,
    IndexersResponse,
    IndexerTestResult,
    IndexerTestResults,
)

router = APIRouter(prefix="/indexers", tags=["Indexers"], dependencies=[Depends(require_api_key)])

_SERVER_ERROR = "Unexpected server error."
_UPSTREAM_ERROR = "Prowlarr could not be reached."
_NOT_CONFIGURED = "Prowlarr is not configured."

INDEXER_RESPONSES = error_responses(
    {
        status.HTTP_502_BAD_GATEWAY: _UPSTREAM_ERROR,
        status.HTTP_503_SERVICE_UNAVAILABLE: _NOT_CONFIGURED,
        status.HTTP_500_INTERNAL_SERVER_ERROR: _SERVER_ERROR,
    }
)

TEST_INDEXER_RESPONSES = error_responses(
    {
        status.HTTP_404_NOT_FOUND: "Indexer not found.",
        status.HTTP_502_BAD_GATEWAY: _UPSTREAM_ERROR,
        status.HTTP_503_SERVICE_UNAVAILABLE: _NOT_CONFIGURED,
        status.HTTP_500_INTERNAL_SERVER_ERROR: _SERVER_ERROR,
    }
)

HISTORY_RESPONSES = error_responses(
    {
        status.HTTP_422_UNPROCESSABLE_CONTENT: "Invalid pagination or filter parameters.",
        status.HTTP_502_BAD_GATEWAY: _UPSTREAM_ERROR,
        status.HTTP_503_SERVICE_UNAVAILABLE: _NOT_CONFIGURED,
        status.HTTP_500_INTERNAL_SERVER_ERROR: _SERVER_ERROR,
    }
)

IndexerIdParam = Annotated[int, Path(..., alias="indexerId")]


def _get_container() -> AppContainer:
    return get_container()


def _list_use_case(container: AppContainer = Depends(_get_container)) -> ListIndexersUseCase:
    return container.use_cases.indexers.list


def _history_use_case(
    container: AppContainer = Depends(_get_container),
) -> ListIndexerHistoryUseCase:
    return container.use_cases.indexers.list_history


def _logs_use_case(container: AppContainer = Depends(_get_container)) -> ListIndexerLogsUseCase:
    return container.use_cases.indexers.list_logs


def _run_test_use_case(container: AppContainer = Depends(_get_container)) -> RunIndexerTestUseCase:
    return container.use_cases.indexers.run_test


def _run_all_tests_use_case(
    container: AppContainer = Depends(_get_container),
) -> RunAllIndexerTestsUseCase:
    return container.use_cases.indexers.run_all_tests


def _dto_to_indexer(dto: IndexerDTO) -> Indexer:
    return Indexer(
        id=dto.indexer_id,
        name=dto.name,
        health=dto.health,
        enabled=dto.enabled,
        protocol=dto.protocol,
        privacy=dto.privacy,
        priority=dto.priority,
        supports_search=dto.supports_search,
        supports_rss=dto.supports_rss,
        indexer_urls=list(dto.indexer_urls),
        disabled_till=dto.disabled_till,
        most_recent_failure=dto.most_recent_failure,
        initial_failure=dto.initial_failure,
    )


def _dto_to_history(page: IndexerHistoryPageDTO) -> IndexerHistoryResponse:
    return IndexerHistoryResponse(
        history=[
            IndexerHistoryEntry(
                id=event.event_id,
                indexer_id=event.indexer_id,
                occurred_at=event.occurred_at,
                event_type=event.event_type,
                successful=event.successful,
                indexer_name=event.indexer_name,
                query=event.query,
                title=event.title,
                source=event.source,
                elapsed_ms=event.elapsed_ms,
                data=dict(event.data),
            )
            for event in page.events
        ],
        total=page.total,
        page=page.page,
        per_page=page.per_page,
    )


def _dto_to_logs(page: IndexerLogsPageDTO) -> IndexerLogsResponse:
    return IndexerLogsResponse(
        logs=[
            IndexerLogEntry(
                id=entry.log_id,
                occurred_at=entry.occurred_at,
                level=entry.level,
                message=entry.message,
                component=entry.component,
                method=entry.method,
                exception=entry.exception,
                exception_type=entry.exception_type,
            )
            for entry in page.logs
        ],
        total=page.total,
        page=page.page,
        per_page=page.per_page,
    )


def _dto_to_test_result(dto: IndexerTestResultDTO) -> IndexerTestResult:
    return IndexerTestResult(
        indexer_id=dto.indexer_id,
        success=dto.success,
        name=dto.name,
        errors=list(dto.errors),
    )


@router.get("", response_model=IndexersResponse, responses=INDEXER_RESPONSES)
async def list_indexers(
    use_case: ListIndexersUseCase = Depends(_list_use_case),
) -> IndexersResponse:
    indexers = await use_case.execute()
    return IndexersResponse(indexers=[_dto_to_indexer(dto) for dto in indexers])


@router.get("/logs", response_model=IndexerLogsResponse, responses=HISTORY_RESPONSES)
async def list_indexer_logs(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1),
    min_level: IndexerLogLevel | None = Query(
        default=None,
        description="Least severe level to return; Prowlarr treats it as a threshold.",
    ),
    use_case: ListIndexerLogsUseCase = Depends(_logs_use_case),
) -> IndexerLogsResponse:
    result = await use_case.execute(page=page, per_page=per_page, min_level=min_level)
    return _dto_to_logs(result)


@router.get("/history", response_model=IndexerHistoryResponse, responses=HISTORY_RESPONSES)
async def list_indexer_history(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1),
    indexer_id: int | None = Query(default=None, alias="indexer_id"),
    event_type: IndexerEventType | None = Query(
        default=None,
        description="Only events of this kind.",
    ),
    use_case: ListIndexerHistoryUseCase = Depends(_history_use_case),
) -> IndexerHistoryResponse:
    result = await use_case.execute(
        page=page,
        per_page=per_page,
        indexer_id=indexer_id,
        event_type=event_type,
    )
    return _dto_to_history(result)


@router.post("/test", response_model=IndexerTestResults, responses=INDEXER_RESPONSES)
async def test_indexers(
    use_case: RunAllIndexerTestsUseCase = Depends(_run_all_tests_use_case),
) -> IndexerTestResults:
    results = await use_case.execute()
    return IndexerTestResults(results=[_dto_to_test_result(dto) for dto in results])


@router.post(
    "/{indexerId}/test",
    response_model=IndexerTestResult,
    responses=TEST_INDEXER_RESPONSES,
)
async def test_indexer(
    indexer_id: IndexerIdParam,
    use_case: RunIndexerTestUseCase = Depends(_run_test_use_case),
) -> IndexerTestResult:
    result = await use_case.execute(indexer_id)
    return _dto_to_test_result(result)


__all__ = ["router"]
