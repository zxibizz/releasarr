"""FastAPI routes for inspecting and testing the configured indexers."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, status

from src.api.dependencies import require_api_key
from src.api.responses import error_responses
from src.application.use_cases.indexers.dto import IndexerDTO, IndexerTestResultDTO
from src.application.use_cases.indexers.list_indexers import ListIndexersUseCase
from src.application.use_cases.indexers.run_indexer_tests import (
    RunAllIndexerTestsUseCase,
    RunIndexerTestUseCase,
)
from src.core.container import AppContainer, get_container
from src.schemas.indexers import (
    Indexer,
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

IndexerIdParam = Annotated[int, Path(..., alias="indexerId")]


def _get_container() -> AppContainer:
    return get_container()


def _list_use_case(container: AppContainer = Depends(_get_container)) -> ListIndexersUseCase:
    return container.use_cases.indexers.list


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
