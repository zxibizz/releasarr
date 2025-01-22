from fastapi import APIRouter

from src.application.models import Show
from src.dependencies import dependencies

api_router = APIRouter()


@api_router.get("/shows/")
async def get_shows(only_missing: bool) -> list[Show]:
    return list(
        await dependencies.queries.list_shows.execute(
            only_missing=only_missing,
        )
    )
