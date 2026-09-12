"""Use case for exporting finished series releases to Sonarr."""

from __future__ import annotations

import posixpath
from dataclasses import dataclass

from loguru._logger import Logger

from src.application.interfaces.media_requests import (
    MediaRequestRepository,
    UpdateMediaRequestData,
)
from src.application.interfaces.releases import (
    ReleaseDownloadService,
    ReleaseFileRecord,
    ReleaseRecord,
    ReleaseRepository,
    ReleaseRequestSnapshot,
)
from src.application.interfaces.sonarr import ManualImportFile, SeriesDetails, SonarrService
from src.application.use_cases.releases.auto_mapping import ReleaseAutoMapper
from src.core.logging import get_logger
from src.domain.enums import MediaRequestStatus


@dataclass(slots=True)
class ExportFinishedSeriesResult:
    """Result summary for the export operation."""

    succeeded: int = 0
    failed: int = 0


class ExportFinishedSeriesUseCase:
    """Orchestrate the export of completed series downloads to Sonarr."""

    def __init__(
        self,
        repository: ReleaseRepository,
        sonarr: SonarrService,
        auto_mapper: ReleaseAutoMapper,
        download_service: ReleaseDownloadService,
        request_repository: MediaRequestRepository | None = None,
        logger: Logger | None = None,
    ) -> None:
        self._repository = repository
        self._sonarr = sonarr
        self._auto_mapper = auto_mapper
        self._download_service = download_service
        self._request_repository = request_repository
        self._logger = logger or get_logger(component="export_finished_series")

    async def execute(self) -> ExportFinishedSeriesResult:
        """Process all finished but not yet exported releases."""

        releases = await self._repository.get_finished_not_exported()
        result = ExportFinishedSeriesResult()

        for release in releases:
            try:
                await self._process_release(release)
                result.succeeded += 1
            except Exception as exc:
                self._logger.error(
                    "Failed to export release",
                    release_id=release.id,
                    release_name=release.name,
                    error=str(exc),
                )
                await self._repository.update_release(
                    release.id, export_failures_count=release.export_failures_count + 1
                )
                result.failed += 1

        return result

    async def _process_release(self, release: ReleaseRecord) -> None:
        # 1. Fill any mapping gaps the grab left behind
        candidates = await self._auto_mapper.apply(release)

        # 2. Group files by Sonarr series ID
        requests_map = {request.id: request for request in candidates}
        files_by_series: dict[int, list[ReleaseFileRecord]] = {}

        for file in release.files:
            if not file.mapping or not file.mapping.request_id:
                continue

            req = requests_map.get(file.mapping.request_id)
            if not req or not req.sonarr_series_id:
                continue

            files_by_series.setdefault(req.sonarr_series_id, []).append(file)

        if not files_by_series:
            return

        # 3. Resolve where the download client put the payload. Sonarr reads the
        # files off the same filesystem, so it needs absolute paths.
        download_dir = await self._download_service.get_download_directory(release.info_hash)
        if not download_dir:
            self._logger.warning(
                "Skipping export: download directory is unknown",
                release_id=release.id,
                release_name=release.name,
                info_hash=release.info_hash,
            )
            return

        # 4. Process each series
        all_import_files: list[ManualImportFile] = []
        imported_seasons: set[tuple[int, int]] = set()

        for series_id, files in files_by_series.items():
            episodes = await self._sonarr.get_episodes(series_id)
            episode_map = {(ep.season_number, ep.episode_number): ep.id for ep in episodes}

            for file in files:
                if not file.mapping or file.mapping.season is None or file.mapping.episode is None:
                    continue

                episode_id = episode_map.get((file.mapping.season, file.mapping.episode))
                if not episode_id:
                    self._logger.warning(
                        "Could not find Sonarr episode ID",
                        series_id=series_id,
                        season=file.mapping.season,
                        episode=file.mapping.episode,
                        file_path=file.path,
                    )
                    continue

                all_import_files.append(
                    ManualImportFile(
                        path=posixpath.join(download_dir, file.path),
                        series_id=series_id,
                        episode_ids=[episode_id],
                        folder_name=release.name,
                    )
                )
                imported_seasons.add((series_id, file.mapping.season))

        if not all_import_files:
            # Nothing resolvable yet: leave the release unexported so a later run can
            # retry once mappings or Sonarr metadata catch up.
            return

        # 5. Trigger import
        success = await self._sonarr.manual_import(all_import_files)

        if not success:
            raise RuntimeError("Sonarr manual import command failed")

        await self._repository.update_release(
            release.id,
            last_exported_info_hash=release.info_hash,
            export_failures_count=0,
        )
        await self._complete_requests(candidates, imported_seasons)

    async def _complete_requests(
        self,
        candidates: list[ReleaseRequestSnapshot],
        imported_seasons: set[tuple[int, int]],
    ) -> None:
        """Close the requests whose season Sonarr now holds in full.

        The Sonarr sync owns this transition everywhere else, but the sequence a
        finished download runs deliberately leaves that task out, so a request
        would otherwise stay in flight until the next hourly sync. Sonarr is
        still asked to confirm rather than assuming the import covered the
        season, since the release may only carry part of it.
        """

        if self._request_repository is None:
            return

        details_by_series: dict[int, SeriesDetails] = {}

        for request in candidates:
            series_id = request.sonarr_series_id
            season_number = request.season_number
            if series_id is None or season_number is None:
                continue
            if (series_id, season_number) not in imported_seasons:
                continue

            details = details_by_series.get(series_id)
            if details is None:
                details = await self._sonarr.get_series(series_id)
                details_by_series[series_id] = details

            season = details.seasons.get(season_number)
            if season is None or not season.episode_count:
                continue
            if season.episode_file_count < season.episode_count:
                continue

            await self._request_repository.update_request(
                request.id,
                UpdateMediaRequestData(status=MediaRequestStatus.COMPLETED),
            )
            self._logger.info(
                "Marked request as completed",
                request_id=request.id,
                sonarr_series_id=series_id,
                season_number=season_number,
            )
