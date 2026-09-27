"""Application entrypoint for the FastAPI app.

Phase 0 keeps the surface minimal: the container is initialized during
lifespan startup so later phases can register dependencies and routers.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src import __version__
from src.api.errors import register_exception_handlers
from src.api.paths import API_PREFIX
from src.api.request_logging import register_request_logging
from src.api.routes import register_routes
from src.core.container import get_container
from src.domain.enums import LogService


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize global singletons on startup and dispose them on shutdown."""

    from sqlalchemy import text

    container = get_container()
    container.startup(service=LogService.API)

    try:
        async with container.db_manager.session() as session:
            await session.execute(text("SELECT 1"))
    except Exception as exc:
        raise RuntimeError("Database connection failed during startup") from exc

    # As with Sonarr/Radarr, the service key always exists; nothing has to create it.
    await container.use_cases.auth.service_key.execute()

    try:
        yield
    finally:
        await container.shutdown()


container = get_container()
app = FastAPI(
    title=container.settings.api_title,
    version=__version__,
    lifespan=lifespan,
    openapi_url=f"{API_PREFIX}/openapi.json",
    docs_url=f"{API_PREFIX}/docs",
)
"""FastAPI ASGI application."""

LOCALHOST_ORIGINS = {
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
}

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(LOCALHOST_ORIGINS),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_routes(app)
register_request_logging(app)
register_exception_handlers(app)


@app.get("/ping", include_in_schema=False)
async def ping() -> JSONResponse:
    """Unauthenticated probe, as the *arr apps serve it: OK only while the database answers."""
    from sqlalchemy import text

    container = get_container()
    try:
        async with container.db_manager.session() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse({"status": "Error"}, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
    return JSONResponse({"status": "OK"})


__all__ = ["app"]


if __name__ == "__main__":
    import uvicorn

    settings = container.settings
    try:
        uvicorn.run(
            app,
            host=settings.api_host,
            port=settings.api_port,
            log_config=None,
            log_level=settings.log_level.lower(),
        )
    except (KeyboardInterrupt, SystemExit):
        pass
