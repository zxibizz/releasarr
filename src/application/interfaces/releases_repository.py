from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.models import Release


class I_ReleasesRepository(Protocol):
    async def create(self, db_session: AsyncSession, release: Release) -> None: ...
