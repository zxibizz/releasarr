"""List media requests with pagination and optional filters."""

from __future__ import annotations

from src.application.interfaces.media_requests import MediaRequestRepository
from src.application.interfaces.request_warnings import RequestWarningRepository
from src.application.use_cases.requests.commands import ListRequestsOptions
from src.application.use_cases.requests.dto import MediaRequestsPageDTO
from src.application.use_cases.requests.mappers import records_to_page
from src.settings.config import AppSettings, get_settings


class ListMediaRequestsUseCase:
    """Use case orchestrating media request listings."""

    def __init__(
        self,
        repository: MediaRequestRepository,
        warning_repository: RequestWarningRepository,
        settings: AppSettings | None = None,
    ) -> None:
        self._repository = repository
        self._warning_repository = warning_repository
        self._settings = settings or get_settings()

    async def execute(self, options: ListRequestsOptions | None = None) -> MediaRequestsPageDTO:
        opts = options or ListRequestsOptions()

        page = self._normalise_page(opts.page)
        per_page = self._normalise_per_page(opts.per_page)

        records, total = await self._repository.list_requests(
            page=page,
            per_page=per_page,
            status=opts.status,
            media_type=opts.media_type,
            owner_user_id=opts.owner_user_id,
            has_warnings=opts.has_warnings,
            active_only=opts.active_only,
            search=opts.search,
            sort=opts.sort,
        )

        warnings_by_request = await self._warning_repository.list_for_requests(
            [record.id for record in records]
        )

        return records_to_page(
            records,
            total=total,
            page=page,
            per_page=per_page,
            warnings_by_request=warnings_by_request,
        )

    def _normalise_page(self, page: int | None) -> int:
        if page is None or page <= 0:
            return self._settings.default_page
        return page

    def _normalise_per_page(self, per_page: int | None) -> int:
        if per_page is None or per_page <= 0:
            per_page = self._settings.default_page_size
        return min(per_page, self._settings.max_page_size)


__all__ = ["ListMediaRequestsUseCase"]
