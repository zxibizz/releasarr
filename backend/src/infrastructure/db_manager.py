from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.db_manager import I_DBManager
from src.db import async_session


class DBManager(I_DBManager):
    def __init__(self) -> None:
        self._make_session_func = async_session

    @asynccontextmanager
    async def begin_session(self) -> AsyncIterator[AsyncSession]:
        async with async_session() as session, session.begin():
            yield session
