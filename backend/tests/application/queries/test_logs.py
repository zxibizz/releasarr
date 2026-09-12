"""Unit tests for the ListLogsQuery."""

from __future__ import annotations

import datetime
from typing import Any

import pytest

from src.application.queries.logs import ListLogsQuery
from src.infrastructure.logs import LogEntry, LogFileReader
from src.settings.config import AppSettings


class MockLogFileReader(LogFileReader):
    def __init__(self, entries: list[LogEntry]) -> None:
        self.entries = entries
        self.last_filter_request_id: str | None = None
        self.last_filter_task: str | None = None

    def read_entries(
        self,
        request_id: str | None = None,
        task: str | None = None,
    ) -> list[LogEntry]:
        self.last_filter_request_id = request_id
        self.last_filter_task = task

        entries = self.entries
        if request_id:
            entries = [
                e for e in entries if e.metadata and e.metadata.get("request_id") == request_id
            ]
        if task:
            entries = [e for e in entries if e.metadata and e.metadata.get("task") == task]
        return entries


@pytest.fixture
def make_entry() -> Any:
    def _make(
        message: str,
        timestamp: float | None = None,
        level: str = "INFO",
        request_id: str | None = None,
        task: str | None = None,
    ) -> LogEntry:
        metadata = {}
        if request_id:
            metadata["request_id"] = request_id
        if task:
            metadata["task"] = task

        return LogEntry(
            id="log-id",
            occurred_at=int((timestamp or 1000.0) * 1000),
            timestamp=str(datetime.datetime.fromtimestamp(timestamp or 1000.0)),
            level=level,
            message=message,
            metadata=metadata,
        )

    return _make


@pytest.fixture
def settings() -> AppSettings:
    return AppSettings(default_page=1, default_page_size=10, max_page_size=50)


def test_list_logs_returns_reversed_entries(make_entry: Any, settings: AppSettings) -> None:
    entries = [
        make_entry("First", timestamp=1000),
        make_entry("Second", timestamp=2000),
        make_entry("Third", timestamp=3000),
    ]
    reader = MockLogFileReader(entries)
    query = ListLogsQuery(reader, settings)

    result = query.execute(page=1, per_page=10)

    assert len(result.logs) == 3
    assert result.logs[0].message == "Third"
    assert result.logs[1].message == "Second"
    assert result.logs[2].message == "First"
    assert result.total == 3


def test_list_logs_paginates_results(make_entry: Any, settings: AppSettings) -> None:
    entries = [make_entry(f"Log {i}") for i in range(10)]
    reader = MockLogFileReader(entries)
    query = ListLogsQuery(reader, settings)

    # Page 1 (items 0-4 of reversed list: Log 9, Log 8, Log 7, Log 6, Log 5)
    result_p1 = query.execute(page=1, per_page=5)
    assert len(result_p1.logs) == 5
    assert result_p1.logs[0].message == "Log 9"
    assert result_p1.total == 10

    # Page 2 (items 5-9 of reversed list: Log 4, Log 3, Log 2, Log 1, Log 0)
    result_p2 = query.execute(page=2, per_page=5)
    assert len(result_p2.logs) == 5
    assert result_p2.logs[0].message == "Log 4"


def test_list_logs_filters_by_request_id(make_entry: Any, settings: AppSettings) -> None:
    entries = [
        make_entry("Log 1", request_id="target-req"),
        make_entry("Log 2", request_id="other-req"),
        make_entry("Log 3", request_id="target-req"),
    ]
    reader = MockLogFileReader(entries)
    query = ListLogsQuery(reader, settings)

    result = query.execute(request_id="target-req")

    assert len(result.logs) == 2
    assert result.logs[0].message == "Log 3"
    assert result.logs[1].message == "Log 1"
    assert reader.last_filter_request_id == "target-req"


def test_list_logs_filters_by_task(make_entry: Any, settings: AppSettings) -> None:
    entries = [
        make_entry("Exported one", task="export"),
        make_entry("Synced downloads", task="release_sync"),
        make_entry("Exported two", task="export"),
    ]
    reader = MockLogFileReader(entries)
    query = ListLogsQuery(reader, settings)

    result = query.execute(task="export")

    assert [entry.message for entry in result.logs] == ["Exported two", "Exported one"]
    assert reader.last_filter_task == "export"


def test_list_logs_combines_request_and_task_filters(
    make_entry: Any, settings: AppSettings
) -> None:
    entries = [
        make_entry("Imported for request", request_id="req-1", task="export"),
        make_entry("Imported for another", request_id="req-2", task="export"),
        make_entry("Synced for request", request_id="req-1", task="release_sync"),
    ]
    reader = MockLogFileReader(entries)
    query = ListLogsQuery(reader, settings)

    result = query.execute(request_id="req-1", task="export")

    assert [entry.message for entry in result.logs] == ["Imported for request"]


def test_list_logs_validates_pagination_params(settings: AppSettings) -> None:
    reader = MockLogFileReader([])
    query = ListLogsQuery(reader, settings)

    with pytest.raises(ValueError):
        query.execute(page=-1)

    with pytest.raises(ValueError):
        query.execute(per_page=-1)
