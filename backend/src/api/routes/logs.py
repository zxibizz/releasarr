"""FastAPI routes for retrieving request logs."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from src.api.dependencies import require_api_key
from src.api.errors import api_error
from src.api.responses import error_responses
from src.application.queries.logs import LogsPageResult
from src.application.use_cases.logs.list_logs import ListLogsUseCase
from src.schemas.enums import RequestLogLevel
from src.schemas.logs import LogsResponse, RequestLogEntry

router = APIRouter(prefix="/logs", tags=["Logs"], dependencies=[Depends(require_api_key)])


def _to_response(result: LogsPageResult) -> LogsResponse:
    return LogsResponse(
        logs=[
            RequestLogEntry(
                id=entry.id,
                occurred_at=entry.occurred_at,
                timestamp=entry.timestamp,
                level=RequestLogLevel(entry.level),
                message=entry.message,
                source=entry.source,
                metadata=entry.metadata,
                stack_trace=entry.stack_trace,
            )
            for entry in result.logs
        ],
        total=result.total,
        page=result.page,
        per_page=result.per_page,
    )


def _get_use_case() -> ListLogsUseCase:
    from src.core.container import get_container

    container = get_container()
    return container.use_cases.logs.list


LOGS_RESPONSES = error_responses(
    {
        status.HTTP_400_BAD_REQUEST: "Invalid pagination or filter parameters.",
        status.HTTP_500_INTERNAL_SERVER_ERROR: "Unexpected server error.",
    }
)


@router.get("", response_model=LogsResponse, responses=LOGS_RESPONSES)
async def list_logs(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1),
    request_id: str | None = Query(default=None, alias="request_id"),
    use_case: ListLogsUseCase = Depends(_get_use_case),
) -> LogsResponse:
    try:
        result = await use_case.execute(page=page, per_page=per_page, request_id=request_id)
    except ValueError as exc:  # pragma: no cover - defensive whilst query validates internally
        raise api_error(status.HTTP_400_BAD_REQUEST, "invalid_logs_query", str(exc)) from exc
    return _to_response(result)


__all__ = ["router"]
