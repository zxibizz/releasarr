"""API router registration helpers."""

from fastapi import APIRouter, FastAPI

from src.api.paths import API_PREFIX
from src.api.routes.auth import router as auth_router
from src.api.routes.discover import router as discover_router
from src.api.routes.indexers import router as indexers_router
from src.api.routes.logs import router as logs_router
from src.api.routes.releases import request_releases_router
from src.api.routes.releases import router as releases_router
from src.api.routes.requests import router as requests_router
from src.api.routes.service_keys import router as service_keys_router
from src.api.routes.settings import router as settings_router
from src.api.routes.system import router as system_router
from src.api.routes.tasks import router as tasks_router
from src.api.routes.users import router as users_router


def register_routes(app: FastAPI) -> None:
    """Attach all routers to the FastAPI application, under the API prefix."""

    api = APIRouter(prefix=API_PREFIX)
    api.include_router(auth_router)
    api.include_router(users_router)
    api.include_router(service_keys_router)
    api.include_router(settings_router)
    api.include_router(system_router)
    api.include_router(requests_router)
    api.include_router(releases_router)
    api.include_router(request_releases_router)
    api.include_router(discover_router)
    api.include_router(logs_router)
    api.include_router(tasks_router)
    api.include_router(indexers_router)
    app.include_router(api)


__all__ = ["register_routes"]
