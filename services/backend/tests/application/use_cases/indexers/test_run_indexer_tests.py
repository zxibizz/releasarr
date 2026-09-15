"""Tests for the indexer test-run use cases."""

from __future__ import annotations

import pytest

from src.application.interfaces.indexers import IndexerTestResultRecord
from src.application.use_cases.indexers.exceptions import ProwlarrNotConfiguredError
from src.application.use_cases.indexers.run_indexer_tests import (
    RunAllIndexerTestsUseCase,
    RunIndexerTestUseCase,
)
from tests.fakes import UnusedIndexerDirectoryCalls


class FakeDirectory(UnusedIndexerDirectoryCalls):
    def __init__(
        self,
        results: list[IndexerTestResultRecord] | None = None,
        *,
        is_configured: bool = True,
    ) -> None:
        self._results = results or []
        self.is_configured = is_configured
        self.tested: list[int] = []
        self.tested_all = 0

    async def test_indexer(self, indexer_id: int) -> IndexerTestResultRecord:
        self.tested.append(indexer_id)
        return self._results[0]

    async def test_all_indexers(self) -> list[IndexerTestResultRecord]:
        self.tested_all += 1
        return self._results


async def test_a_single_test_is_forwarded_and_mapped() -> None:
    directory = FakeDirectory(
        [IndexerTestResultRecord(indexer_id=2, success=False, name="Zeta", errors=("Timed out",))]
    )
    use_case = RunIndexerTestUseCase(directory=directory)

    result = await use_case.execute(2)

    assert directory.tested == [2]
    assert result.indexer_id == 2
    assert result.success is False
    assert result.name == "Zeta"
    assert result.errors == ("Timed out",)


async def test_all_results_are_mapped() -> None:
    directory = FakeDirectory(
        [
            IndexerTestResultRecord(indexer_id=1, success=True, name="Alpha"),
            IndexerTestResultRecord(indexer_id=2, success=False, name="Zeta", errors=("Nope",)),
        ]
    )
    use_case = RunAllIndexerTestsUseCase(directory=directory)

    results = await use_case.execute()

    assert directory.tested_all == 1
    assert [(result.indexer_id, result.success) for result in results] == [(1, True), (2, False)]


async def test_testing_without_prowlarr_configured_raises() -> None:
    unconfigured = FakeDirectory(is_configured=False)

    with pytest.raises(ProwlarrNotConfiguredError):
        await RunIndexerTestUseCase(directory=unconfigured).execute(1)

    with pytest.raises(ProwlarrNotConfiguredError):
        await RunAllIndexerTestsUseCase(directory=unconfigured).execute()
