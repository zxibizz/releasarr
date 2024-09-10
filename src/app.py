import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager

from src.services.releases import ReleasesService
from src.services.shows import ShowService

load_dotenv()


app = FastAPI()

templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def missing(request: Request):
    shows = ShowService()

    data = await shows.get_missing()
    return templates.TemplateResponse(
        "requests.html", {"request": request, "shows": data}
    )


@app.get("/show/{show_id}")
async def show_page(request: Request, show_id: int):
    shows = ShowService()

    show = await shows.get_show(show_id)
    return templates.TemplateResponse("show.html", {"request": request, "show": show})


@app.post("/show/{show_id}/search")
async def search_show(request: Request, show_id: int, query: str = Form(...)):
    shows = ShowService()
    await shows.search_show_releases(show_id, query)
    return RedirectResponse(url=f"/show/{show_id}", status_code=303)


@app.post("/show/{show_id}/grab")
async def grab(
    show_id: int,
    search: str = Form(...),
    search_name: str = Form(...),
    download_url: str = Form(...),
):
    releases = ReleasesService()
    await releases.grab(show_id, search, search_name, download_url)
    return RedirectResponse(url=f"/show/{show_id}", status_code=303)


@app.post("/show/{show_id}/release/{release_name}/file_matching")
async def update_file_matching(
    request: Request,
    show_id: int,
    release_name: str,
):
    form_data = await request.form()
    updated_file_matching = []
    i = 1
    prev_season_number = None
    prev_episode_number = None

    while f"file_name_{i}" in form_data:
        season_number = form_data[f"season_number_{i}"]
        episode_number = form_data[f"episode_number_{i}"]

        if (
            not season_number
            and not episode_number
            and prev_season_number
            and prev_episode_number
        ):
            season_number = prev_season_number
            episode_number = int(prev_episode_number) + 1

        updated_file_matching.append(
            {
                "file_name": form_data[f"file_name_{i}"],
                "season_number": season_number,
                "episode_number": episode_number,
            }
        )
        prev_season_number = season_number
        prev_episode_number = episode_number
        i += 1
    releases = ReleasesService()
    await releases.update_file_matching(release_name, updated_file_matching)

    return RedirectResponse(url=f"/show/{show_id}", status_code=303)


# TODO: Periodic tasks:
# - Search release updates for missing shows having a release matched to the missing season


async def sync_missing_task():
    shows = ShowService()
    while True:
        await shows.sync_missing()
        await asyncio.sleep(60)


async def sync_finished_task():
    shows = ShowService()
    releases = ReleasesService()

    while True:
        finished_shows = await releases.get_shows_having_finished_releases()
        for show_id in finished_shows:
            await shows.sync_show_release_files(show_id)
        await asyncio.sleep(60)
        


@asynccontextmanager
async def lifespan():
    asyncio.create_task(sync_missing_task())
    asyncio.create_task(sync_finished_task())
    yield


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
