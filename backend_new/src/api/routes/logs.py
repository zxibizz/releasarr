"""FastAPI routes for retrieving request logs."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from src.api.dependencies import require_api_key
from src.api.errors import api_error
from src.application.use_cases.logs.list_logs import ListLogsUseCase
from src.schemas.logs import LogsResponse

router = APIRouter(prefix="/logs", tags=["Logs"], dependencies=[Depends(require_api_key)])


def _get_use_case() -> ListLogsUseCase:
    from src.core.container import get_container

    container = get_container()
    query = container.resolve("list_logs_query")
    return ListLogsUseCase(query=query)


@router.get("", response_model=LogsResponse)
async def list_logs(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1),
    request_id: str | None = Query(default=None, alias="request_id"),
    use_case: ListLogsUseCase = Depends(_get_use_case),
) -> LogsResponse:
    try:
        return await use_case.execute(page=page, per_page=per_page, request_id=request_id)
    except ValueError as exc:  # pragma: no cover - defensive whilst query validates internally
        raise api_error(status.HTTP_400_BAD_REQUEST, "invalid_logs_query", str(exc)) from exc


__all__ = ["router"]
