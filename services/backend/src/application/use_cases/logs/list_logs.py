"""Use case for returning paginated logs to the application layer."""

from __future__ import annotations

import asyncio
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
        service: str | None = None,
        component: str | None = None,
        min_level: str | None = None,
    ) -> LogsPageResult:
        # The query parses every line of the log files to find its matches, which
        # is far too much blocking work to run on the event loop.
        return await asyncio.to_thread(
            self.query.execute,
            page=page,
            per_page=per_page,
            request_id=request_id,
            task=task,
            service=service,
            component=component,
            min_level=min_level,
        )
