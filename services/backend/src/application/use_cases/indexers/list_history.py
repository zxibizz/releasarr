"""List the events a search provider recorded against its indexers."""

from __future__ import annotations

from src.application.interfaces.indexers import IndexerDirectory, IndexerEventRecord
from src.application.use_cases.indexers.dto import IndexerEventDTO, IndexerHistoryPageDTO
from src.application.use_cases.indexers.exceptions import ProwlarrNotConfiguredError
from src.application.use_cases.indexers.pagination import normalise_page, normalise_per_page
from src.core.logging import get_logger
from src.domain.enums import IndexerEventType
from src.settings.config import AppSettings, get_settings

logger = get_logger(component="indexers")


class ListIndexerHistoryUseCase:
    def __init__(
        self,
        directory: IndexerDirectory,
        settings: AppSettings | None = None,
    ) -> None:
        self._directory = directory
        self._settings = settings or get_settings()

    async def execute(
        self,
        page: int | None = None,
        per_page: int | None = None,
        indexer_id: int | None = None,
        event_type: IndexerEventType | None = None,
    ) -> IndexerHistoryPageDTO:
        if not self._directory.is_configured:
            raise ProwlarrNotConfiguredError

        page = normalise_page(page, self._settings)
        per_page = normalise_per_page(per_page, self._settings)

        result = await self._directory.list_history(
            page=page,
            per_page=per_page,
            indexer_id=indexer_id,
            event_type=event_type,
        )

        logger.debug(
            "Listed indexer history",
            page=page,
            per_page=per_page,
            returned=len(result.events),
            total=result.total,
            indexer_id=indexer_id,
            event_type=event_type.value if event_type else None,
        )
        return IndexerHistoryPageDTO(
            events=tuple(self._to_dto(record) for record in result.events),
            total=result.total,
            page=page,
            per_page=per_page,
        )

    def _to_dto(self, record: IndexerEventRecord) -> IndexerEventDTO:
        return IndexerEventDTO(
            event_id=record.event_id,
            indexer_id=record.indexer_id,
            occurred_at=record.occurred_at,
            event_type=record.event_type,
            successful=record.successful,
            indexer_name=record.indexer_name,
            query=record.query,
            title=record.title,
            source=record.source,
            elapsed_ms=record.elapsed_ms,
            data=dict(record.data),
        )


__all__ = ["ListIndexerHistoryUseCase"]
