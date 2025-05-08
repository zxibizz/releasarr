from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

_engine = None
_AsyncSessionLocal = None


async def init_db(db_connection_string: str):
    global _engine, _AsyncSessionLocal

    _engine = create_async_engine(
        db_connection_string,
        echo=False,
    )

    _AsyncSessionLocal = sessionmaker(
        _engine, class_=AsyncSession, expire_on_commit=False
    )


async def get_session():
    async with _AsyncSessionLocal() as session:
        yield session
