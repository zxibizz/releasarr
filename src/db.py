import os

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

load_dotenv()

DB_PATH = os.environ.get("DB_PATH")

async_engine = create_async_engine(f"sqlite+aiosqlite:///{DB_PATH}", echo=True)
async_session = async_sessionmaker(async_engine, expire_on_commit=False)
