from typing import AsyncIterator, Protocol

from sqlalchemy.ext.asyncio import AsyncSession


class I_DBManager(Protocol):
    async def begin_session(self) -> AsyncIterator[AsyncSession]: ...
