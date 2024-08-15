import os
from dataclasses import dataclass
from datetime import datetime

import httpx


@dataclass
class SonarrSeries:
    id: int
    path: str
    tvdb_id: str
    seasons: list["SonarrSeason"]


@dataclass
class SonarrSeason:
    season_number: int
    episode_file_count: int
    episode_count: int
    total_episodes_count: int
    previous_airing: datetime | None


@dataclass
class SonarrMissingSeries:
    id: int
    tvdb_id: int
    season_numbers: list[int]


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
        seasons: list[SonarrSeason] = [
            SonarrSeason(
                season_number=season_data["seasonNumber"],
                episode_file_count=season_data["statistics"]["episodeFileCount"],
                episode_count=season_data["statistics"]["episodeCount"],
                total_episodes_count=season_data["statistics"]["totalEpisodeCount"],
                previous_airing=season_data["statistics"].get("previousAiring"),
            )
            for season_data in series_data["seasons"]
        ]
        return SonarrSeries(
            id=series_data["id"],
            path=series_data["path"],
            tvdb_id=series_data["tvdbId"],
            seasons=seasons,
        )


if __name__ == "__main__":
    import asyncio

    client = SonarrApiClient()
    res = asyncio.run(client.get_missing())
    print(res)
    # print("\n".join([str(row) for row in res]))
