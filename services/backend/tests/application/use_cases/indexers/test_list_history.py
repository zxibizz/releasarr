"""Tests for the indexer history use case."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from src.application.interfaces.indexers import IndexerEventPage, IndexerEventRecord
from src.application.use_cases.indexers.exceptions import ProwlarrNotConfiguredError
from src.application.use_cases.indexers.list_history import ListIndexerHistoryUseCase
from src.domain.enums import IndexerEventType
from src.settings.config import get_settings
from tests.fakes import UnusedIndexerDirectoryCalls


class FakeDirectory(UnusedIndexerDirectoryCalls):
    def __init__(
        self,
        events: tuple[IndexerEventRecord, ...] = (),
        total: int = 0,
        *,
        is_configured: bool = True,
    ) -> None:
        self._page = IndexerEventPage(events=events, total=total)
        self.is_configured = is_configured
        self.calls: list[dict[str, object]] = []

    async def list_history(
        self,
        *,
        page: int,
        per_page: int,
        indexer_id: int | None = None,
        event_type: IndexerEventType | None = None,
    ) -> IndexerEventPage:
        self.calls.append(
            {
                "page": page,
                "per_page": per_page,
                "indexer_id": indexer_id,
                "event_type": event_type,
            }
        )
        return self._page


def _event(**overrides: object) -> IndexerEventRecord:
    defaults: dict[str, object] = {
        "event_id": 412,
        "indexer_id": 2,
        "occurred_at": datetime(2026, 3, 4, 11, 59, tzinfo=UTC),
        "event_type": IndexerEventType.INDEXER_QUERY,
        "successful": True,
    }
    return IndexerEventRecord(**(defaults | overrides))  # type: ignore[arg-type]


def _use_case(directory: FakeDirectory) -> ListIndexerHistoryUseCase:
    return ListIndexerHistoryUseCase(directory=directory, settings=get_settings())


async def test_the_page_carries_every_field_through() -> None:
    directory = FakeDirectory(
        events=(
            _event(
                indexer_name="Zeta Tracker",
                query="Severance S02",
                title="Severance.S02E01.2160p",
                source="Sonarr",
                elapsed_ms=412,
                data={"host": "sonarr.example"},
            ),
        ),
        total=57,
    )

    result = await _use_case(directory).execute(page=2, per_page=25)

    assert result.total == 57
    assert result.page == 2
    assert result.per_page == 25

    event = result.events[0]
    assert event.event_id == 412
    assert event.indexer_id == 2
    assert event.indexer_name == "Zeta Tracker"
    assert event.event_type is IndexerEventType.INDEXER_QUERY
    assert event.successful is True
    assert event.query == "Severance S02"
    assert event.title == "Severance.S02E01.2160p"
    assert event.source == "Sonarr"
    assert event.elapsed_ms == 412
    assert event.data == {"host": "sonarr.example"}


async def test_the_filters_reach_the_provider() -> None:
    directory = FakeDirectory()

    await _use_case(directory).execute(
        indexer_id=2,
        event_type=IndexerEventType.RELEASE_GRABBED,
    )

    assert directory.calls[0]["indexer_id"] == 2
    assert directory.calls[0]["event_type"] is IndexerEventType.RELEASE_GRABBED


async def test_pagination_falls_back_to_the_configured_defaults() -> None:
    directory = FakeDirectory()
    settings = get_settings()

    await _use_case(directory).execute(page=None, per_page=None)

    assert directory.calls[0]["page"] == settings.default_page
    assert directory.calls[0]["per_page"] == settings.default_page_size


async def test_an_oversized_page_is_capped_rather_than_forwarded() -> None:
    """Prowlarr would happily serve thousands of rows in one response."""

    directory = FakeDirectory()
    settings = get_settings()

    await _use_case(directory).execute(per_page=settings.max_page_size + 500)

    assert directory.calls[0]["per_page"] == settings.max_page_size


async def test_history_without_prowlarr_configured_is_an_error_not_an_empty_page() -> None:
    use_case = ListIndexerHistoryUseCase(
        directory=FakeDirectory(is_configured=False), settings=get_settings()
    )

    with pytest.raises(ProwlarrNotConfiguredError):
        await use_case.execute()
