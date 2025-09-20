from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.services.releases import ReleaseService


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_session():
        yield session


async def get_release_service(
    session: AsyncSession = Depends(get_db),
) -> ReleaseService:
    return ReleaseService(session)
