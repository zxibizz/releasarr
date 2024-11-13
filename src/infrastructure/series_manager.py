import os

import httpx

from src.application.interfaces.series_service import (
    I_SeriesService,
    MissingSeries,
    Series,
    SeriesImportFile,
)


class SeriesService(I_SeriesService):
    def __init__(self) -> None:
        self.base_url = os.environ.get("SONARR_BASE_URL")
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"X-Api-Key": os.environ.get("SONARR_API_TOKEN")},
        )

    async def get_missing(self) -> list[MissingSeries]:
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
            existing_row: MissingSeries = result_data.get(key)
            if not existing_row:
                result_data[key] = MissingSeries(
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

    async def get_series(self, series_id) -> Series: ...

    async def manual_import(self, import_files: list[SeriesImportFile]) -> None: ...
