from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from src.services.releases import ReleasesService
from src.services.shows import ShowService

load_dotenv()


app = FastAPI()

templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def missing(request: Request):
    shows = ShowService()

    # TODO: move to a async task
    await shows.sync_missing()

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
    request: Request,
    show_id: int,
    search: str = Form(...),
    download_url: str = Form(...),
):
    releases = ReleasesService()
    await releases.grab(show_id, search, download_url)
    return RedirectResponse(url=f"/show/{show_id}", status_code=303)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
