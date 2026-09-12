"""Query for listing log entries from structured log files."""

from __future__ import annotations

from dataclasses import dataclass

from src.infrastructure.logs import LogEntry, LogFileReader
from src.settings.config import AppSettings


@dataclass(slots=True)
class LogsPageResult:
    """Paginated log entries result."""

    logs: list[LogEntry]
    total: int
    page: int
    per_page: int


@dataclass(slots=True)
class ListLogsQuery:
    """Query handler for retrieving paginated log entries.

    Reads from the Loguru JSON log file and applies pagination
    and optional request_id or task filtering.
    """

    reader: LogFileReader
    settings: AppSettings

    def execute(
        self,
        page: int | None = None,
        per_page: int | None = None,
        request_id: str | None = None,
        task: str | None = None,
    ) -> LogsPageResult:
        """Return a page of log entries.

        Args:
            page: 1-indexed page number (defaults to settings.default_page)
            per_page: Items per page (defaults to settings.default_page_size)
            request_id: Optional filter by request identifier
            task: Optional filter by the background task that logged the entry

        Returns:
            Paginated result with log entries.
        """
        page = page or self.settings.default_page
        per_page = min(per_page or self.settings.default_page_size, self.settings.max_page_size)

        if page < 1:
            raise ValueError("page must be >= 1")
        if per_page < 1:
            raise ValueError("per_page must be >= 1")

        all_entries = self.reader.read_entries(request_id=request_id, task=task)
        # Most recent logs first
        all_entries = list(reversed(all_entries))

        total = len(all_entries)
        start = (page - 1) * per_page
        end = start + per_page
        page_entries = all_entries[start:end]

        return LogsPageResult(
            logs=page_entries,
            total=total,
            page=page,
            per_page=per_page,
        )


__all__ = ["ListLogsQuery", "LogsPageResult"]
