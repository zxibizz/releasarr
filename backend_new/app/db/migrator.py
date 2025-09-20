from __future__ import annotations

import asyncio
from pathlib import Path

from alembic import command
from alembic.config import Config


def _alembic_config(database_url: str) -> Config:
    base_path = Path(__file__).resolve().parents[2]
    cfg = Config(str(base_path / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", database_url)
    cfg.set_main_option("script_location", str(base_path / "alembic"))
    return cfg


async def run_migrations(database_url: str) -> None:
    cfg = _alembic_config(database_url)
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, command.upgrade, cfg, "head")
