from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.models import Show
from src.application.schemas import ReleaseData


class I_ShowsRepository(Protocol):
    async def get_show_with_releases(
        self, db_session: AsyncSession, show_id: int
    ) -> Show | None:
        raise NotImplementedError

    async def get_series(self, db_session: AsyncSession, series_id: int) -> Show | None:
        raise NotImplementedError

    async def save_releases_seach_results(
        self,
        db_session: AsyncSession,
        show_id: int,
        search_string: str,
        releases_search_result: list[ReleaseData],
    ) -> None:
        raise NotImplementedError

    async def unflag_all_missing_series(self, db_session: AsyncSession) -> None:
        raise NotImplementedError

    async def save(self, db_session: AsyncSession, show: Show) -> None:
        raise NotImplementedError
