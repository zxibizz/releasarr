from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from dependencies.sonarr import SonarrApiClient
from dependencies.tvdb import TVDBApiClient

load_dotenv()


sonarr_api_client = SonarrApiClient()
tvdb_api_client = TVDBApiClient()


app = FastAPI()

templates = Jinja2Templates(directory="templates")

series_list = [
    {
        "title": "Пацаны",
        "year": 2019,
        "image_url": "https://placehold.co/300x450?text=Preview+not+found.jpg",
        "seasons": [2, 4],
    },
    {
        "title": "Чистые",
        "year": 2024,
        "image_url": "https://placehold.co/300x450?text=Preview+not+found.jpg",
        "seasons": [1],
    },
    {
        "title": "Друзья",
        "year": 1994,
        "image_url": "https://placehold.co/300x450?text=Preview+not+found.jpg",
        "seasons": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    },
]


@app.get("/", response_class=HTMLResponse)
async def read_item(request: Request):
    missing_series = await sonarr_api_client.get_missing()
    data = []
    for m in missing_series:
        tvdb_data = await tvdb_api_client.get_series(m.tvdb_id)
        data.append(
            {
                "title": tvdb_data.title,
                "year": tvdb_data.year,
                "image_url": tvdb_data.image_url,
                "seasons": m.season_numbers,
            },
        )

    return templates.TemplateResponse(
        "requests.html", {"request": request, "series_list": data}
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
