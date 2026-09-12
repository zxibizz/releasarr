"""Use case for returning paginated logs to the application layer."""

from __future__ import annotations

from dataclasses import dataclass

from src.application.queries.logs import ListLogsQuery, LogsPageResult


@dataclass(slots=True)
class ListLogsUseCase:
    query: ListLogsQuery

    async def execute(
        self,
        page: int,
        per_page: int,
        request_id: str | None = None,
        task: str | None = None,
    ) -> LogsPageResult:
        return self.query.execute(
            page=page,
            per_page=per_page,
            request_id=request_id,
            task=task,
        )
