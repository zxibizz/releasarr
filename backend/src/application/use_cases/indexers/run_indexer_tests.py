"""Exercise indexers to confirm they work and lift their failure back-off.

Named around "run" rather than "test" so pytest does not try to collect any of
this as a test suite of its own.
"""

from __future__ import annotations

from src.application.interfaces.indexers import IndexerDirectory, IndexerTestResultRecord
from src.application.use_cases.indexers.dto import IndexerTestResultDTO
from src.application.use_cases.indexers.exceptions import ProwlarrNotConfiguredError
from src.core.logging import get_logger

logger = get_logger(component="indexers")


def _to_dto(record: IndexerTestResultRecord) -> IndexerTestResultDTO:
    return IndexerTestResultDTO(
        indexer_id=record.indexer_id,
        success=record.success,
        name=record.name,
        errors=tuple(record.errors),
    )


class RunIndexerTestUseCase:
    def __init__(self, directory: IndexerDirectory | None) -> None:
        self._directory = directory

    async def execute(self, indexer_id: int) -> IndexerTestResultDTO:
        if self._directory is None:
            raise ProwlarrNotConfiguredError

        result = await self._directory.test_indexer(indexer_id)
        logger.info("Tested indexer", indexer_id=indexer_id, success=result.success)
        return _to_dto(result)


class RunAllIndexerTestsUseCase:
    def __init__(self, directory: IndexerDirectory | None) -> None:
        self._directory = directory

    async def execute(self) -> list[IndexerTestResultDTO]:
        if self._directory is None:
            raise ProwlarrNotConfiguredError

        results = [_to_dto(record) for record in await self._directory.test_all_indexers()]
        logger.info(
            "Tested all indexers",
            total=len(results),
            failed=sum(1 for result in results if not result.success),
        )
        return results


__all__ = ["RunAllIndexerTestsUseCase", "RunIndexerTestUseCase"]
