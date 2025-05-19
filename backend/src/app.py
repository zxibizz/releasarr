from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.dependencies import dependencies
from src.routes import api_router
from src.settings import app_settings


@asynccontextmanager
async def lifespan(_: FastAPI):
    if app_settings.ENABLE_TASK_SCHEDULER:
        await dependencies.task_scheduler.start()

    yield

    if app_settings.ENABLE_TASK_SCHEDULER:
        await dependencies.task_scheduler.stop()


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


if __name__ == "__main__":
    import uvicorn

    try:
        uvicorn.run(app, host="0.0.0.0", port=8000, log_config=None)
    except (InterruptedError, KeyboardInterrupt):
        pass
