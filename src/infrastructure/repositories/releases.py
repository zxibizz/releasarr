from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.application.interfaces.releases_repository import I_ReleasesRepository
from src.application.models import Release, ReleaseFileMatching


class ReleasesRepository(I_ReleasesRepository):
    async def create(self, db_session: AsyncSession, release: Release) -> None:
        db_session.add(release)

    async def get(self, db_session: AsyncSession, name: str) -> Release | None:
        return await db_session.scalar(
            select(Release)
            .where(Release.name == name)
            .options(joinedload(Release.file_matchings))
        )

    async def update_file_matchings(
        self, db_session: AsyncSession, file_matchings: list[ReleaseFileMatching]
    ) -> None:
        db_session.add_all(file_matchings)
