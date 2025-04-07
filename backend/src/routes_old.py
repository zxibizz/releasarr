from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from src.application.use_cases.releases.update_files_matching import (
    DTO_ReleaseFileMatchingUpdate,
)
from src.dependencies import dependencies

templates = Jinja2Templates(directory="templates")
views_router = APIRouter()


@views_router.get("/", response_class=HTMLResponse)
async def missing(request: Request):
    data = await dependencies.queries.list_shows.execute(only_missing=True)
    return templates.TemplateResponse(
        "requests.html", {"request": request, "shows": data}
    )


@views_router.get("/show/{show_id}")
async def show_page(request: Request, show_id: int):
    show = await dependencies.queries.get_show.execute(show_id)
    return templates.TemplateResponse("show.html", {"request": request, "show": show})


@views_router.post("/show/{show_id}/search")
async def search_show(request: Request, show_id: int, query: str = Form(...)):
    await dependencies.use_cases.search_release.process(show_id, query)
    return RedirectResponse(url=f"/show/{show_id}", status_code=303)


@views_router.post("/show/{show_id}/grab")
async def grab(show_id: int, release_pk: str = Form(...)):
    await dependencies.use_cases.grab_release.process(
        show_id=show_id, release_pk=release_pk
    )
    return RedirectResponse(url=f"/show/{show_id}", status_code=303)


@views_router.post("/show/{show_id}/release/{release_name}/file_matching")
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


@views_router.post("/show/{show_id}/release/{release_name}/delete")
async def delete_release(show_id: int, release_name: str):
    await dependencies.use_cases.delete_release.process(release_name)


@views_router.get("/logs", response_class=HTMLResponse)
async def logs(request: Request):
    logs_data = await dependencies.queries.list_logs.execute()
    return templates.TemplateResponse(
        "logs.html", {"request": request, "logs": logs_data.records}
    )


@views_router.get("/sync")
@views_router.post("/sync")
async def sync():
    await dependencies.task_scheduler.trigger_sync_task()
