import asyncio
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import delete, select

from src.application.models import Release, ReleaseFileMatching
from src.application.use_cases.releases.update_files_matching import (
    DTO_ReleaseFileMatchingUpdate,
)
from src.db import async_session
from src.dependencies import dependencies
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
            await dependencies.use_cases.sync_missing_series.process()
            await dependencies.use_cases.import_releases_torrent_stats.process()
            await dependencies.use_cases.export_finished_series.process()
            await dependencies.use_cases.re_grab_outdated_releases.process()

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
