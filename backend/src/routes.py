from fastapi import APIRouter, Body, HTTPException

from src.application.models import Show
from src.application.use_cases.releases.update_files_matching import (
    DTO_ReleaseFileMatchingUpdate,
)
from src.dependencies import dependencies
from src.infrastructure.queries.get_show import DTO_Show
from src.infrastructure.queries.list_logs import DTO_Logs

api_router = APIRouter()


@api_router.get("/shows/")
async def get_shows(only_missing: bool) -> list[Show]:
    return await dependencies.queries.list_shows.execute(
        only_missing=only_missing,
    )


@api_router.get("/shows/{show_id}", response_model=DTO_Show)
async def get_show(show_id: int) -> Show:
    show = await dependencies.queries.get_show.execute(show_id)
    if show is None:
        raise HTTPException(status_code=404, detail="Show not found")
    return show


@api_router.post("/shows/{show_id}/search_release")
async def search_show_release(show_id: int, query: str = Body(..., embed=True)):
    await dependencies.use_cases.search_release.process(show_id, query)
    return {"status": "ok"}


@api_router.post("/shows/{show_id}/grab")
async def grab_show_release(show_id: int, release_pk: str = Body(..., embed=True)):
    await dependencies.use_cases.grab_release.process(
        show_id=show_id, release_pk=release_pk
    )
    return {"status": "ok"}


@api_router.post("/shows/{show_id}/file_matching")
async def update_release_file_matchings(
    show_id: int,
    release_name: str = Body(..., embed=True),
    updated_file_matchings: list[DTO_ReleaseFileMatchingUpdate] = Body(..., embed=True),
):
    await dependencies.use_cases.update_release_file_matchings.process(
        show_id, release_name, updated_file_matchings
    )
    return {"status": "ok"}


@api_router.delete("/shows/{show_id}/releases/{release_name}")
async def delete_release(show_id: int, release_name: str):
    await dependencies.use_cases.delete_release.process(name=release_name)
    return {"status": "ok"}


@api_router.get("/logs")
async def get_logs() -> DTO_Logs:
    return await dependencies.queries.list_logs.execute()


@api_router.get("/tasks/sync_all")
@api_router.post("/tasks/sync_all")
async def sync():
    await dependencies.task_scheduler.trigger_sync_task()
