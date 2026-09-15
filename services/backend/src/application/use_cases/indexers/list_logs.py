"""List the search provider's own log."""

from __future__ import annotations

from src.application.interfaces.indexers import IndexerDirectory, IndexerLogRecord
from src.application.use_cases.indexers.dto import IndexerLogDTO, IndexerLogsPageDTO
from src.application.use_cases.indexers.exceptions import ProwlarrNotConfiguredError
from src.application.use_cases.indexers.pagination import normalise_page, normalise_per_page
from src.core.logging import get_logger
from src.domain.enums import IndexerLogLevel
from src.settings.config import AppSettings, get_settings

logger = get_logger(component="indexers")


class ListIndexerLogsUseCase:
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
        min_level: IndexerLogLevel | None = None,
    ) -> IndexerLogsPageDTO:
        if not self._directory.is_configured:
            raise ProwlarrNotConfiguredError

        page = normalise_page(page, self._settings)
        per_page = normalise_per_page(per_page, self._settings)

        result = await self._directory.list_logs(
            page=page,
            per_page=per_page,
            min_level=min_level,
        )

        logger.debug(
            "Listed indexer logs",
            page=page,
            per_page=per_page,
            returned=len(result.logs),
            total=result.total,
            min_level=min_level.value if min_level else None,
        )
        return IndexerLogsPageDTO(
            logs=tuple(self._to_dto(record) for record in result.logs),
            total=result.total,
            page=page,
            per_page=per_page,
        )

    def _to_dto(self, record: IndexerLogRecord) -> IndexerLogDTO:
        return IndexerLogDTO(
            log_id=record.log_id,
            occurred_at=record.occurred_at,
            level=record.level,
            message=record.message,
            component=record.component,
            method=record.method,
            exception=record.exception,
            exception_type=record.exception_type,
        )


__all__ = ["ListIndexerLogsUseCase"]
