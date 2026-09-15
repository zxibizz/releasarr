"""Tests for the indexer listing use case and its health derivation."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from src.application.interfaces.indexers import IndexerRecord
from src.application.use_cases.indexers.exceptions import ProwlarrNotConfiguredError
from src.application.use_cases.indexers.list_indexers import ListIndexersUseCase
from src.domain.enums import IndexerHealth
from tests.fakes import UnusedIndexerDirectoryCalls

NOW = datetime(2026, 3, 4, 12, 0, tzinfo=UTC)


class FakeDirectory(UnusedIndexerDirectoryCalls):
    def __init__(self, records: list[IndexerRecord], *, is_configured: bool = True) -> None:
        self._records = records
        self.is_configured = is_configured

    async def list_indexers(self) -> list[IndexerRecord]:
        return self._records


def _record(**overrides: object) -> IndexerRecord:
    defaults: dict[str, object] = {
        "indexer_id": 1,
        "name": "Tracker",
        "enabled": True,
    }
    return IndexerRecord(**(defaults | overrides))  # type: ignore[arg-type]


def _use_case(records: list[IndexerRecord]) -> ListIndexersUseCase:
    return ListIndexersUseCase(directory=FakeDirectory(records), clock=lambda: NOW)


async def test_an_indexer_with_no_failures_is_healthy() -> None:
    indexers = await _use_case([_record()]).execute()

    assert indexers[0].health is IndexerHealth.HEALTHY


async def test_a_switched_off_indexer_is_disabled_whatever_its_history() -> None:
    """A cleared enable flag is deliberate, so it outranks the failure log."""

    indexers = await _use_case(
        [
            _record(
                enabled=False,
                disabled_till=datetime(2026, 3, 4, 18, 0, tzinfo=UTC),
                most_recent_failure=datetime(2026, 3, 4, 11, 0, tzinfo=UTC),
            )
        ]
    ).execute()

    assert indexers[0].health is IndexerHealth.DISABLED


async def test_an_indexer_in_its_back_off_window_is_blocked() -> None:
    indexers = await _use_case(
        [
            _record(
                disabled_till=datetime(2026, 3, 4, 18, 0, tzinfo=UTC),
                most_recent_failure=datetime(2026, 3, 4, 11, 0, tzinfo=UTC),
            )
        ]
    ).execute()

    assert indexers[0].health is IndexerHealth.BLOCKED


async def test_an_indexer_whose_back_off_expired_is_only_degraded() -> None:
    """Prowlarr keeps the failure timestamps until a query succeeds."""

    indexers = await _use_case(
        [
            _record(
                disabled_till=datetime(2026, 3, 4, 6, 0, tzinfo=UTC),
                most_recent_failure=datetime(2026, 3, 4, 5, 0, tzinfo=UTC),
                initial_failure=datetime(2026, 3, 3, 22, 0, tzinfo=UTC),
            )
        ]
    ).execute()

    assert indexers[0].health is IndexerHealth.DEGRADED


async def test_failures_without_a_back_off_window_are_degraded() -> None:
    indexers = await _use_case(
        [_record(most_recent_failure=datetime(2026, 3, 4, 11, 0, tzinfo=UTC))]
    ).execute()

    assert indexers[0].health is IndexerHealth.DEGRADED


async def test_every_field_is_carried_through() -> None:
    indexers = await _use_case(
        [
            _record(
                indexer_id=7,
                name="Zeta",
                protocol="torrent",
                privacy="private",
                priority=25,
                supports_search=True,
                supports_rss=True,
                indexer_urls=("https://zeta.example/",),
            )
        ]
    ).execute()

    indexer = indexers[0]
    assert indexer.indexer_id == 7
    assert indexer.name == "Zeta"
    assert indexer.protocol == "torrent"
    assert indexer.privacy == "private"
    assert indexer.priority == 25
    assert indexer.supports_search is True
    assert indexer.supports_rss is True
    assert indexer.indexer_urls == ("https://zeta.example/",)


async def test_listing_without_prowlarr_configured_is_an_error_not_an_empty_list() -> None:
    """An empty list would read as "no indexers" rather than "no Prowlarr"."""

    use_case = ListIndexersUseCase(directory=FakeDirectory([], is_configured=False))

    with pytest.raises(ProwlarrNotConfiguredError):
        await use_case.execute()
