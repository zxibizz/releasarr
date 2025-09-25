"""List releases with pagination and optional filters."""

from __future__ import annotations

from src.application.interfaces.releases import ReleaseRepository
from src.application.use_cases.releases.commands import ListReleasesOptions
from src.application.use_cases.releases.dto import ReleasesPageDTO
from src.application.use_cases.releases.mappers import records_to_page
from src.settings.config import AppSettings, get_settings


class ListReleasesUseCase:
    """Use case orchestrating release listings."""

    def __init__(
        self,
        repository: ReleaseRepository,
        settings: AppSettings | None = None,
    ) -> None:
        self._repository = repository
        self._settings = settings or get_settings()

    async def execute(self, options: ListReleasesOptions | None = None) -> ReleasesPageDTO:
        opts = options or ListReleasesOptions()

        page = self._normalise_page(opts.page)
        per_page = self._normalise_per_page(opts.per_page)

        records, total = await self._repository.list_releases(
            page=page,
            per_page=per_page,
            status=opts.status,
            request_id=opts.request_id,
        )

        return records_to_page(records, total=total, page=page, per_page=per_page)

    def _normalise_page(self, page: int | None) -> int:
        if page is None or page <= 0:
            return self._settings.default_page
        return page

    def _normalise_per_page(self, per_page: int | None) -> int:
        if per_page is None or per_page <= 0:
            per_page = self._settings.default_page_size
        return min(per_page, self._settings.max_page_size)


__all__ = ["ListReleasesUseCase"]
