import os

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

load_dotenv()

DB_PATH = os.environ.get("DB_PATH")
DB_CONNECTION_URL = f"sqlite+aiosqlite:///{DB_PATH}"

async_engine = create_async_engine(DB_CONNECTION_URL, echo=False)
async_session = async_sessionmaker(async_engine, expire_on_commit=False)
