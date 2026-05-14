"""API router registration helpers."""

from fastapi import FastAPI

from src.api.routes.logs import router as logs_router
from src.api.routes.releases import request_releases_router
from src.api.routes.releases import router as releases_router
from src.api.routes.requests import router as requests_router


def register_routes(app: FastAPI) -> None:
    """Attach all routers to the FastAPI application."""

    app.include_router(requests_router)
    app.include_router(releases_router)
    app.include_router(request_releases_router)
    app.include_router(logs_router)


__all__ = ["register_routes"]
