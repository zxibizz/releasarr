from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.models import Show
from src.application.schemas import ReleaseData


class I_ShowsRepository(Protocol):
    async def get_show_with_releases(
        self, db_session: AsyncSession, show_id: int
    ) -> Show | None: ...

    async def save_releases_seach_results(
        self,
        db_session: AsyncSession,
        show_id: int,
        search_string: str,
        releases_search_result: list[ReleaseData],
    ): ...
