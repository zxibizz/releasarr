from functools import cache

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine


@cache
def get_async_engine(db_path: str) -> AsyncEngine:
    DB_CONNECTION_URL = f"sqlite+aiosqlite:///{db_path}"
    return create_async_engine(DB_CONNECTION_URL, echo=False)


@cache
def get_async_sessionmaker(db_path: str) -> async_sessionmaker:
    async_engine = get_async_engine(db_path)
    return async_sessionmaker(async_engine, expire_on_commit=False)
