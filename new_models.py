import os

import asyncio
from venv import create
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlmodel import Field, SQLModel
from dotenv import load_dotenv

load_dotenv()


class SonarrSeries(SQLModel, table=True):
    id: int = Field(primary_key=True)
    tvdb_id: str = ""
    tvdb_year: str = ""
    tvdb_country: str = ""
    tvdb_title: str = ""
    tvdb_title_en: str = ""
    tvdb_image_url: str = ""
    tvdb_overview: str = ""


class SonarrSeason:
    ...


class SonarrEpisode:
    ...


class SonarrMissingEpisode:
    sonarr_episode_id: int # FK


class Release:
    ...
    name: str
    info_hash: str
    total_size: int
    creation_date: "datetime"
    prowlarr_query: str
    prowlarr_guid: str
    prowlarr_indexer: str
    sonarr_show: int
    prowlarr_movie: int


#???
class ReleaseSeasonMatching:
    ...


class ReleaseFileMatching:
    release: int
    order: int
    file_name: str
    sonarr_season: int
    sonarr_episode: int
    prowlarr_movie: int


DB_PATH = os.environ.get("DB_PATH")

async_engine = create_async_engine(f"sqlite+aiosqlite://{DB_PATH}", echo=True)
async_session = async_sessionmaker(async_engine, expire_on_commit=False)

engine = create_engine(f"sqlite:///sqlite.db", echo=True)

async def main():
    SQLModel.metadata.create_all(engine)

if __name__ == "__main__":
    asyncio.run(main())