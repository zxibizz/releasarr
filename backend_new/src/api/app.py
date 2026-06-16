"""Application entrypoint for the FastAPI app.

Phase 0 keeps the surface minimal: the container is initialized during
lifespan startup so later phases can register dependencies and routers.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError

from src.api.errors import (
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
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
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)


@app.get("/healthz")
async def healthcheck() -> dict[str, str]:
    """Simple health endpoint to aid local development."""

    return {"status": "ok"}


__all__ = ["app"]
