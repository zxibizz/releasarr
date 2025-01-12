from fastapi import APIRouter, HTTPException

from src.application.models import Show
from src.dependencies import dependencies

api_router = APIRouter()


@api_router.get("/shows/")
async def get_shows(only_missing: bool) -> list[Show]:
    return await dependencies.queries.list_shows.execute(
        only_missing=only_missing,
    )


@api_router.get("/shows/{show_id}")
async def get_show(show_id: int) -> Show:
    show = await dependencies.queries.get_show.execute(show_id)
    if show is None:
        raise HTTPException(status_code=404, detail="Show not found")
    return show
