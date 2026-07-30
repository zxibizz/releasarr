"""Application entrypoint for the FastAPI app.

Phase 0 keeps the surface minimal: the container is initialized during
lifespan startup so later phases can register dependencies and routers.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
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
    
    # Verify DB connectivity
    try:
        from sqlalchemy import text
        async with container.db_manager.session() as session:
            await session.execute(text("SELECT 1"))
    except Exception as exc:
        # In a real deployment we might want to prevent startup, 
        # but for now we'll just log or re-raise
        raise RuntimeError("Database connection failed during startup") from exc

    try:
        yield
    finally:
        # Ensure http clients are closed
        if container.repositories:
            # Check if any repo needs cleanup (none currently do, but good practice)
            pass
            
        # Services cleanup - specifically search/lifecycle clients if they exist
        # The container shutdown method usually handles this if implemented correctly
        # Let's verify container shutdown implementation
        await container.shutdown()


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


@app.get("/readyz")
async def readiness_probe() -> dict[str, str]:
    """Check application dependencies."""
    from sqlalchemy import text
    
    container = get_container()
    try:
        async with container.db_manager.session() as session:
            await session.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connectivity failed"
        ) from exc
    return {"status": "ready"}


@app.get("/healthz")
async def healthcheck() -> dict[str, str]:
    """Simple health endpoint to aid local development."""

    return {"status": "ok"}


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
