from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.application.interfaces.db_manager import I_DBManager


class DBManager(I_DBManager):
    def __init__(self, sessionmaker: async_sessionmaker) -> None:
        self._sessionmaker = sessionmaker

    @asynccontextmanager
    async def begin_session(self) -> AsyncIterator[AsyncSession]:
        async with self._sessionmaker() as session, session.begin():
            yield session
