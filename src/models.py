import asyncio
import os

from dotenv import load_dotenv
from sqlalchemy import types
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import Field, SQLModel

load_dotenv()


class Release(SQLModel, table=True):
    name: str = Field(primary_key=True)
    data: dict = Field(default_factory=dict, sa_type=types.JSON)
    # info_hash: str
    # total_size: int
    # creation_date: "datetime"
    # prowlarr_query: str
    # prowlarr_guid: str
    # prowlarr_indexer: str
    # sonarr_series_id: int
    # prowlarr_movie: int


DB_PATH = os.environ.get("DB_PATH")

async_engine = create_async_engine(f"sqlite+aiosqlite:///{DB_PATH}", echo=True)
async_session = async_sessionmaker(async_engine, expire_on_commit=False)


async def main():
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)

    async with async_session() as session, session.begin():
        session.add(Release(name="Test", data={"da": {"data": [111]}}))
        await session.commit()


if __name__ == "__main__":
    asyncio.run(main())


"""
"""
