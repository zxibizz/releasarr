from __future__ import annotations

import asyncio

from fastapi import FastAPI
from loguru import logger

from app.api.routes import releases as releases_router
from app.api.routes import requests as requests_router
from app.api.routes import torrents as torrents_router
from app.clients.factory import get_clients
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.migrator import run_migrations
from app.db.session import engine
from app import models  # noqa: F401  # ensure models registered


def create_app() -> FastAPI:
    configure_logging()

    settings = get_settings()
    app = FastAPI(title=settings.app_name)

    app.include_router(requests_router.router)
    app.include_router(releases_router.router)
    app.include_router(torrents_router.router)

    @app.on_event("startup")
    async def on_startup() -> None:  # pragma: no cover
        logger.info("Starting Releasarr backend")
        await run_migrations(settings.database_url)

    @app.on_event("shutdown")
    async def on_shutdown() -> None:  # pragma: no cover
        logger.info("Shutting down Releasarr backend")
        clients = get_clients()
        await asyncio.gather(
            clients.sonarr.close(),
            clients.tvdb.close(),
            clients.prowlarr.close(),
            clients.qbittorrent.close(),
        )
        await engine.dispose()

    return app


app = create_app()
