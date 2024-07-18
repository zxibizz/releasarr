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
    series_id: int
    season_number: int
    episode_ids: list


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
                "includeSeries": "false",
                "includeImages": "false",
                "monitored": "true",
            },
        )
        response_data = res.json()["records"]
        result_data = {}
        result: list[SonarrMissingSeries] = []

        for response_data_row in response_data:
            key = response_data_row["seriesId"], response_data_row["seasonNumber"]
            existing_row: SonarrMissingSeries = result_data.get(key)
            if not existing_row:
                result_data[key] = SonarrMissingSeries(
                    series_id=key[0],
                    season_number=key[1],
                    episode_ids=[response_data_row["id"]],
                )
            else:
                existing_row.episode_ids.append(response_data_row["id"])
        result = sorted(
            result_data.values(), key=lambda row: (row.series_id, row.season_number)
        )
        return result

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
    res = asyncio.run(client.get_series(253))
    print(res)
    # print("\n".join([str(row) for row in res]))
