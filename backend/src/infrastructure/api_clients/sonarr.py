import httpx

from src.application.interfaces.series_service import (
    E_SeriesManualImportError,
    Episode,
    I_SeriesService,
    MissingSeries,
    Season,
    Series,
    SeriesImportFile,
)


class SonarrApiClient(I_SeriesService):
    def __init__(self, base_url, api_token) -> None:
        self.client = httpx.AsyncClient(
            base_url=base_url, headers={"X-Api-Key": api_token}
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

    async def get_series(self, series_id) -> Series:
        res = await self.client.get(
            f"series/{series_id}",
            params={"includeSeasonImages": "false"},
        )
        series_data = res.json()
        seasons: list[Series] = []
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
                Season(
                    season_number=season_data["seasonNumber"],
                    episode_file_count=season_data["statistics"]["episodeFileCount"],
                    episode_count=season_data["statistics"]["episodeCount"],
                    episodes=[
                        Episode(
                            id=episode_data["id"],
                            episode_number=episode_data["episodeNumber"],
                        )
                        for episode_data in episodes_data
                    ],
                    total_episodes_count=season_data["statistics"]["totalEpisodeCount"],
                    previous_airing=season_data["statistics"].get("previousAiring"),
                )
            )
        return Series(
            id=series_data["id"],
            path=series_data["path"],
            tvdb_id=series_data["tvdbId"],
            seasons=seasons,
        )

    async def manual_import(self, import_files: list[SeriesImportFile]) -> None:
        try:
            await self._run_manual_import_check(import_files)
            await self._run_manual_import_command(import_files)
        except Exception:
            raise E_SeriesManualImportError

    async def _run_manual_import_check(
        self, import_files: list[SeriesImportFile]
    ) -> None:
        # `POST manualImport` will return 500 in cases when the import file
        # does not exist. This is usefull because this really may take place when
        # qBittoorent didn't gather the downloaded file into the target path yet

        res = await self.client.post(
            "/manualImport",
            json=[
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
        )
        res.raise_for_status()

    async def _run_manual_import_command(
        self, import_files: list[SeriesImportFile]
    ) -> None:
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
