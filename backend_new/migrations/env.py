import asyncio
import importlib
import os
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.db import Base
from app.settings import app_settings


# Import all models to ensure they are registered with the Base metadata
def import_all_models():
    """Import all models to ensure they are registered with Base.metadata."""
    app_dir = Path(__file__).parent.parent / "app"
    for root, _, files in os.walk(app_dir):
        for file in files:
            if file.endswith("models.py"):
                # Convert file path to module path
                module_path = os.path.join(root, file)
                module_path = module_path.replace(str(app_dir.parent), "")
                module_path = module_path.replace(".py", "")
                module_path = module_path.replace(os.sep, ".")
                if module_path.startswith("."):
                    module_path = module_path[1:]

                # Import the module
                try:
                    importlib.import_module(module_path)
                except ImportError as e:
                    print(f"Failed to import {module_path}: {e}")


# Import all models
import_all_models()

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", app_settings.DB_CONNECTION_STRING)

target_metadata = Base.metadata


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    raise Exception

run_migrations_online()
