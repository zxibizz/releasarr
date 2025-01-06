import os
from datetime import datetime

import httpx
from pydantic import BaseModel


class SonarrSeries(BaseModel):
    id: int
    path: str
    tvdb_id: int
    seasons: list["SonarrSeason"]


class SonarrSeason(BaseModel):
    season_number: int
    episode_file_count: int
    episode_count: int
    episodes: list["SonarrEpisode"]
    total_episodes_count: int
    previous_airing: datetime | None


class SonarrEpisode(BaseModel):
    id: int
    episode_number: int


class SonarrMissingSeries(BaseModel):
    id: int
    tvdb_id: int
    season_numbers: list[int]


class SonarrImportFile(BaseModel):
    episode_ids: list[int]
    folder_name: str
    indexer_flags: int = 0
    # languages
    path: str
    # quantity
    release_type: str = "singleEpisode"
    series_id: int


class SonarrApiClient:
    def __init__(self) -> None:
        self.base_url = os.environ.get("SONARR_BASE_URL")
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"X-Api-Key": os.environ.get("SONARR_API_TOKEN")},
        )

    async def get_missing(self) -> list[SonarrMissingSeries]:
        res = await self.client.get(
            "/wanted/missing",
            params={
                "page": "1",
                "pageSize": "1000",
                "includeSeries": "true",
                "includeImages": "false",
                "monitored": "true",
            },
        )
        response_data = res.json()["records"]
        result_data = {}

        for response_data_row in response_data:
            key = response_data_row["seriesId"]
            existing_row: SonarrMissingSeries = result_data.get(key)
            if not existing_row:
                result_data[key] = SonarrMissingSeries(
                    id=key,
                    tvdb_id=response_data_row["series"]["tvdbId"],
                    season_numbers=[response_data_row["seasonNumber"]],
                )
            else:
                existing_row.season_numbers = sorted(
                    set(
                        [
                            *existing_row.season_numbers,
                            response_data_row["seasonNumber"],
                        ]
                    )
                )
        return result_data.values()

    async def get_series(self, series_id) -> SonarrSeries:
        res = await self.client.get(
            f"series/{series_id}",
            params={"includeSeasonImages": "false"},
        )
        series_data = res.json()
        seasons: list[SonarrSeason] = []
        for season_data in series_data["seasons"]:
            episodes_data = (
                await self.client.get(
                    "episode",
                    params={
                        "seriesId": series_id,
                        "seasonNumber": season_data["seasonNumber"],
                    },
                )
            ).json()
            seasons.append(
                SonarrSeason(
                    season_number=season_data["seasonNumber"],
                    episode_file_count=season_data["statistics"]["episodeFileCount"],
                    episode_count=season_data["statistics"]["episodeCount"],
                    episodes=[
                        SonarrEpisode(
                            id=episode_data["id"],
                            episode_number=episode_data["episodeNumber"],
                        )
                        for episode_data in episodes_data
                    ],
                    total_episodes_count=season_data["statistics"]["totalEpisodeCount"],
                    previous_airing=season_data["statistics"].get("previousAiring"),
                )
            )
        return SonarrSeries(
            id=series_data["id"],
            path=series_data["path"],
            tvdb_id=series_data["tvdbId"],
            seasons=seasons,
        )

    async def manual_import(self, import_files: list[SonarrImportFile]):
        res = await self.client.post(
            "/command",
            json={
                "importMode": "copy",
                "name": "ManualImport",
                "files": [
                    {
                        "episodeIds": file.episode_ids,
                        "indexerFlags": file.indexer_flags,
                        "languages": [{"id": 11, "name": "Russian"}],
                        "path": file.path,
                        "quality": {
                            "quality": {
                                "id": 9,
                                "name": "HDTV-1080p",
                                "source": "television",
                                "resolution": 1080,
                            },
                            "revision": {"version": 1, "real": 0, "isRepack": False},
                        },
                        "releaseType": file.release_type,
                        "seriesId": file.series_id,
                    }
                    for file in import_files
                ],
            },
        )
        res.raise_for_status()


if __name__ == "__main__":
    import asyncio

    client = SonarrApiClient()
    res = asyncio.run(client.get_missing())
    print(res)
    # print("\n".join([str(row) for row in res]))
