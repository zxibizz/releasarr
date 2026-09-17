"""API router registration helpers."""

from fastapi import FastAPI

from src.api.routes.auth import router as auth_router
from src.api.routes.discover import router as discover_router
from src.api.routes.indexers import router as indexers_router
from src.api.routes.logs import router as logs_router
from src.api.routes.releases import request_releases_router
from src.api.routes.releases import router as releases_router
from src.api.routes.requests import router as requests_router
from src.api.routes.service_keys import router as service_keys_router
from src.api.routes.settings import router as settings_router
from src.api.routes.tasks import router as tasks_router
from src.api.routes.users import router as users_router


def register_routes(app: FastAPI) -> None:
    """Attach all routers to the FastAPI application."""

    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(service_keys_router)
    app.include_router(settings_router)
    app.include_router(requests_router)
    app.include_router(releases_router)
    app.include_router(request_releases_router)
    app.include_router(discover_router)
    app.include_router(logs_router)
    app.include_router(tasks_router)
    app.include_router(indexers_router)


__all__ = ["register_routes"]
