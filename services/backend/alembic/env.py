"""Alembic environment configuration."""

from __future__ import annotations

import asyncio
import pathlib
import sys

from sqlalchemy import pool
from sqlalchemy.engine import Connection, make_url
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Ensure the project root (containing the ``src`` package) is on ``sys.path``.
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

import src.domain.models  # noqa: E402, F401  (ensure models are registered with metadata)
from src.db import metadata  # noqa: E402  (import after path injection)
from src.settings.config import get_settings  # noqa: E402

settings = get_settings()
config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

target_metadata = metadata


def _to_sync_driver(url: str) -> str:
    """Generate a sync dialect URL for offline migrations."""

    sa_url = make_url(url)
    drivername = sa_url.drivername

    replacements: dict[str, str] = {
        "sqlite+aiosqlite": "sqlite",
        "postgresql+asyncpg": "postgresql",
        "mysql+asyncmy": "mysql",
    }

    new_driver = replacements.get(drivername)
    if new_driver is None and "+" in drivername:
        # Generic fallback that strips the async part after the first '+'
        new_driver = drivername.split("+", maxsplit=1)[0]

    if new_driver is None:
        return str(sa_url)

    sa_url = sa_url.set(drivername=new_driver)
    return str(sa_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""

    url = _to_sync_driver(settings.database_url)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    configuration = config.get_section(config.config_ini_section) or {}
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
