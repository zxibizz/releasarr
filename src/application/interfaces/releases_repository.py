from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.models import Release, ReleaseFileMatching


class I_ReleasesRepository(Protocol):
    async def create(self, db_session: AsyncSession, release: Release) -> None: ...

    async def get(self, db_session: AsyncSession, name: str) -> Release | None: ...

    async def update_file_matchings(
        self, db_session: AsyncSession, file_matchings: list[ReleaseFileMatching]
    ) -> None: ...
