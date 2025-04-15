from functools import cache

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from src.settings import app_settings


@cache
def get_async_engine() -> AsyncEngine:
    return create_async_engine(app_settings.DB_CONNECTION_STRING, echo=False)


@cache
def get_async_sessionmaker() -> async_sessionmaker:
    async_engine = get_async_engine()
    return async_sessionmaker(async_engine, expire_on_commit=False)
