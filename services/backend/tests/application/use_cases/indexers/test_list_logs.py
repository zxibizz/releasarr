"""Tests for the indexer log use case."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from src.application.interfaces.indexers import IndexerLogPage, IndexerLogRecord
from src.application.use_cases.indexers.exceptions import ProwlarrNotConfiguredError
from src.application.use_cases.indexers.list_logs import ListIndexerLogsUseCase
from src.domain.enums import IndexerLogLevel
from src.settings.config import get_settings
from tests.fakes import UnusedIndexerDirectoryCalls


class FakeDirectory(UnusedIndexerDirectoryCalls):
    def __init__(
        self,
        logs: tuple[IndexerLogRecord, ...] = (),
        total: int = 0,
        *,
        is_configured: bool = True,
    ) -> None:
        self._page = IndexerLogPage(logs=logs, total=total)
        self.is_configured = is_configured
        self.calls: list[dict[str, object]] = []

    async def list_logs(
        self,
        *,
        page: int,
        per_page: int,
        min_level: IndexerLogLevel | None = None,
    ) -> IndexerLogPage:
        self.calls.append({"page": page, "per_page": per_page, "min_level": min_level})
        return self._page


def _record(**overrides: object) -> IndexerLogRecord:
    defaults: dict[str, object] = {
        "log_id": 9000,
        "occurred_at": datetime(2026, 3, 4, 11, 58, tzinfo=UTC),
        "level": IndexerLogLevel.WARN,
        "message": "Request for RuTracker.org failed with status 525.",
    }
    return IndexerLogRecord(**(defaults | overrides))  # type: ignore[arg-type]


def _use_case(directory: FakeDirectory) -> ListIndexerLogsUseCase:
    return ListIndexerLogsUseCase(directory=directory, settings=get_settings())


async def test_the_page_carries_every_field_through() -> None:
    directory = FakeDirectory(
        logs=(
            _record(
                component="RuTracker",
                method="GET",
                exception="System.Net.Http.HttpRequestException: boom",
                exception_type="System.Net.Http.HttpRequestException",
            ),
        ),
        total=318,
    )

    result = await _use_case(directory).execute(page=2, per_page=50)

    assert (result.total, result.page, result.per_page) == (318, 2, 50)

    entry = result.logs[0]
    assert entry.log_id == 9000
    assert entry.level is IndexerLogLevel.WARN
    assert entry.message == "Request for RuTracker.org failed with status 525."
    assert entry.component == "RuTracker"
    assert entry.method == "GET"
    assert entry.exception == "System.Net.Http.HttpRequestException: boom"
    assert entry.exception_type == "System.Net.Http.HttpRequestException"


async def test_the_level_threshold_reaches_the_provider() -> None:
    directory = FakeDirectory()

    await _use_case(directory).execute(min_level=IndexerLogLevel.ERROR)

    assert directory.calls[0]["min_level"] is IndexerLogLevel.ERROR


async def test_pagination_falls_back_to_the_configured_defaults() -> None:
    directory = FakeDirectory()
    settings = get_settings()

    await _use_case(directory).execute(page=None, per_page=None)

    assert directory.calls[0]["page"] == settings.default_page
    assert directory.calls[0]["per_page"] == settings.default_page_size


async def test_an_oversized_page_is_capped_rather_than_forwarded() -> None:
    directory = FakeDirectory()
    settings = get_settings()

    await _use_case(directory).execute(per_page=settings.max_page_size + 500)

    assert directory.calls[0]["per_page"] == settings.max_page_size


async def test_logs_without_prowlarr_configured_is_an_error_not_an_empty_page() -> None:
    use_case = ListIndexerLogsUseCase(
        directory=FakeDirectory(is_configured=False), settings=get_settings()
    )

    with pytest.raises(ProwlarrNotConfiguredError):
        await use_case.execute()
