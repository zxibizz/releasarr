import asyncio
import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import delete, select

from src.application.models import Release, ReleaseFileMatching
from src.db import async_session
from src.dependencies import dependencies
from src.services.releases import ReleasesService
from src.services.shows import ShowService

load_dotenv()

logging.getLogger().setLevel(logging.INFO)


RUN_SYNC = False


templates = Jinja2Templates(directory="templates")


async def trigger_sync_task():
    global RUN_SYNC
    while True:
        RUN_SYNC = True
        await asyncio.sleep(60 * 60)


async def sync_task():
    global RUN_SYNC
    while True:
        if not RUN_SYNC:
            await asyncio.sleep(5)
            continue

        logging.info("Running full sync")

        try:
            shows = ShowService()
            releases = ReleasesService()

            await shows.sync_missing()

            finished_shows = await releases.get_shows_having_finished_releases()
            for show_id in finished_shows:
                await shows.sync_show_release_files(show_id)

            missing_releases = await shows.get_outdated_releases()
            for missing_release in missing_releases:
                await releases.re_grab(missing_release.name)

            RUN_SYNC = False
            logging.info("Full sync finished")
        except Exception:
            logging.exception("Failed full sync")


@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(trigger_sync_task())
    asyncio.create_task(sync_task())
    yield


app = FastAPI(lifespan=lifespan)


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
    form_data = await request.form()
    updated_file_matching = []
    i = 1
    prev_season_number = None
    prev_episode_number = None
    prev_dir = None

    while f"file_name_{i}" in form_data:
        season_number = form_data[f"season_number_{i}"]
        episode_number = form_data[f"episode_number_{i}"]
        dir = os.path.dirname(form_data[f"file_name_{i}"])

        if prev_dir != dir:
            prev_season_number = None
            prev_episode_number = None

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
        prev_dir = dir
        i += 1
    releases = ReleasesService()
    await releases.update_file_matching(release_name, updated_file_matching)

    return RedirectResponse(url=f"/show/{show_id}", status_code=303)


@app.post("/show/{show_id}/release/{release_name}/delete")
async def delete_release(show_id: int, release_name: str):
    async with async_session() as session, session.begin():
        release = await session.scalar(
            select(Release).where(Release.name == release_name)
        )
        await session.execute(
            delete(ReleaseFileMatching).where(ReleaseFileMatching.release == release)
        )
        await session.delete(release)
        await session.commit()


@app.get("/sync")
@app.post("/sync")
async def sync():
    global RUN_SYNC
    RUN_SYNC = True


if __name__ == "__main__":
    # from src.db import async_session

    # async def m():
    #     shows_service = ShowService()

    #     shows = await shows_service.get_all()
    #     for show_r in shows:
    #         show = await shows_service.get_show(show_r.id)
    #         async with async_session() as session, session.begin():
    #             for release in show.releases:
    #                 release_data = [
    #                     d
    #                     for d in show.prowlarr_data
    #                     if d.guid == release.prowlarr_guid
    #                     or d.info_url == release.prowlarr_guid
    #                 ]
    #                 print(release.name, release_data)
    #                 if release_data:
    #                     release.prowlarr_data_raw = release_data[0].model_dump_json()
    #                     session.add(release)
    #                 else:
    #                     session.delete(release)
    #         await session.commit()

    # asyncio.run(m())
    # exit(0)
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
