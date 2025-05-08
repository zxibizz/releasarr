import asyncio
import logging
import sys
from pathlib import Path

import click

from src.apps.sonarr.client import SonarrApiClient
from src.apps.sonarr.sync_missing_series import SyncMissingSeries
from src.db.core import init_db
from src.settings import app_settings


def setup_logging():
    log_file = Path(app_settings.LOG_FILE)
    log_file.parent.mkdir(exist_ok=True)

    logger = logging.getLogger("releasarr")
    logger.setLevel(logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(console_formatter)

    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(file_formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


async def run_sync_missing_series():
    logger = setup_logging()
    logger.info("Starting sync_missing_series CLI")

    try:
        # Initialize database
        await init_db(app_settings.DB_CONNECTION_STRING)

        # Create Sonarr client
        sonarr_client = SonarrApiClient(
            base_url=app_settings.SONARR_BASE_URL,
            api_token=app_settings.SONARR_API_TOKEN,
        )

        # Create a database session
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.orm import sessionmaker

        engine = create_async_engine(
            app_settings.DB_CONNECTION_STRING,
            echo=False,
        )

        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )

        async with async_session() as session:
            # Create and run SyncMissingSeries
            sync_service = SyncMissingSeries(
                db_session=session, sonarr_client=sonarr_client, logger=logger
            )

            await sync_service.process()

        logger.info("Sync missing series completed successfully")

    except Exception as e:
        logger.error(f"Error running sync_missing_series: {str(e)}")
        raise


@click.group()
def cli():
    """Releasarr CLI tools."""
    pass


@cli.command(name="sync-missing-series")
def sync_missing_series():
    """Sync missing series from Sonarr."""
    asyncio.run(run_sync_missing_series())


if __name__ == "__main__":
    cli()
