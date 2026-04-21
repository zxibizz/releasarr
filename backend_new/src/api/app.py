"""Application entrypoint for the FastAPI app.

Phase 0 keeps the surface minimal: the container is initialized during
lifespan startup so later phases can register dependencies and routers.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.routes import register_routes
from src.core.container import get_container


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize global singletons when the app starts."""

    container = get_container()
    container.startup()
    try:
        yield
    finally:
        container.shutdown()


container = get_container()
app = FastAPI(
    title=container.settings.api_title,
    version=container.settings.api_version,
    lifespan=lifespan,
)
"""FastAPI ASGI application."""

register_routes(app)


@app.get("/healthz")
async def healthcheck() -> dict[str, str]:
    """Simple health endpoint to aid local development."""

    return {"status": "ok"}


__all__ = ["app"]
