from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.releases_repository import I_ReleasesRepository
from src.application.models import Release


class ReleasesRepository(I_ReleasesRepository):
    async def create(self, db_session: AsyncSession, release: Release) -> None:
        db_session.add(release)
