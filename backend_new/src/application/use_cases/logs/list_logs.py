"""Use case for returning paginated logs to the API layer."""

from __future__ import annotations

from dataclasses import dataclass

from src.application.queries.logs import ListLogsQuery
from src.schemas.logs import LogsResponse, RequestLogEntry


@dataclass(slots=True)
class ListLogsUseCase:
    query: ListLogsQuery

    async def execute(self, page: int, per_page: int, request_id: str | None = None) -> LogsResponse:
        result = self.query.execute(page=page, per_page=per_page, request_id=request_id)
        return LogsResponse(
            logs=[
                RequestLogEntry(
                    id=entry.id,
                    occurred_at=entry.occurred_at,
                    timestamp=entry.timestamp,
                    level=entry.level,
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
