from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from src.application.use_cases.releases.update_files_matching import (
    DTO_ReleaseFileMatchingUpdate,
)
from src.dependencies import dependencies
from src.logger import logger
from src.routes import api_router

RUN_SYNC = False


templates = Jinja2Templates(directory="templates")


async def trigger_sync_task_each_hour():
    global RUN_SYNC
    while True:
        RUN_SYNC = True
        await asyncio.sleep(60 * 60)


async def trigger_sync_task(after: int = 0):
    global RUN_SYNC
    await asyncio.sleep(after)
    RUN_SYNC = True


async def start_sync_task():
    task_logger = logger.bind(component="Tasks.Sync")
    global RUN_SYNC
    while True:
        if not RUN_SYNC:
            await asyncio.sleep(5)
            continue

        task_logger.info("Running full sync")

        try:
            await dependencies.use_cases.sync_missing_series.process()
            await dependencies.use_cases.import_releases_torrent_stats.process()
            export_finished_series_result = (
                await dependencies.use_cases.export_finished_series.process()
            )
            if export_finished_series_result.failed > 0:
                task_logger.warning(
                    f"We have {export_finished_series_result.failed} releases failed to export! "
                    "Rescheduling the sync..."
                )
                asyncio.create_task(trigger_sync_task(after=10))

            await dependencies.use_cases.re_grab_outdated_releases.process()

            RUN_SYNC = False
            task_logger.info("Full sync finished")
        except Exception:
            task_logger.exception("Failed full sync")


@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(start_sync_task())
    asyncio.create_task(trigger_sync_task_each_hour())
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(api_router, prefix="/api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
async def missing(request: Request):
    data = await dependencies.queries.list_shows.execute(only_missing=True)
    return templates.TemplateResponse(
        "requests.html", {"request": request, "shows": data}
    )


@app.get("/show/{show_id}")
async def show_page(request: Request, show_id: int):
    show = await dependencies.queries.get_show.execute(show_id)
    return templates.TemplateResponse("show.html", {"request": request, "show": show})


@app.post("/show/{show_id}/search")
async def search_show(request: Request, show_id: int, query: str = Form(...)):
    await dependencies.use_cases.search_release.process(show_id, query)
    return RedirectResponse(url=f"/show/{show_id}", status_code=303)


@app.post("/show/{show_id}/grab")
async def grab(show_id: int, release_pk: str = Form(...)):
    await dependencies.use_cases.grab_release.process(
        show_id=show_id, release_pk=release_pk
    )
    return RedirectResponse(url=f"/show/{show_id}", status_code=303)


@app.post("/show/{show_id}/release/{release_name}/file_matching")
async def update_file_matching(
    request: Request,
    show_id: int,
    release_name: str,
):
    dto: list[DTO_ReleaseFileMatchingUpdate] = []
    form_data = await request.form()
    i = 1
    while f"file_name_{i}" in form_data:
        dto.append(
            DTO_ReleaseFileMatchingUpdate(
                id=form_data[f"id_{i}"],
                season_number=form_data[f"season_number_{i}"] or None,
                episode_number=form_data[f"episode_number_{i}"] or None,
            )
        )
        i += 1

    await dependencies.use_cases.update_release_file_matchings.process(
        show_id=show_id,
        release_name=release_name,
        updated_file_matchings=dto,
    )

    return RedirectResponse(url=f"/show/{show_id}", status_code=303)


@app.post("/show/{show_id}/release/{release_name}/delete")
async def delete_release(show_id: int, release_name: str):
    await dependencies.use_cases.delete_release.process(release_name)


@app.get("/logs", response_class=HTMLResponse)
async def logs(request: Request):
    logs_data = await dependencies.queries.list_logs.execute()
    return templates.TemplateResponse(
        "logs.html", {"request": request, "logs": logs_data.records}
    )


@app.get("/sync")
@app.post("/sync")
async def sync():
    await trigger_sync_task()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
