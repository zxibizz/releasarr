from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
