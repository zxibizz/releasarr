"""Use case for exporting finished series releases to Sonarr."""

from __future__ import annotations

import json
from dataclasses import dataclass
import os

from loguru._logger import Logger

from src.application.interfaces.releases import (
    ReleaseRepository,
    ReleaseRecord,
)
from src.application.interfaces.sonarr import ManualImportFile, SonarrService
from src.application.utility.file_matcher import ReleaseFileMatcher
from src.core.logging import get_logger


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
        file_matcher: ReleaseFileMatcher,
        logger: Logger | None = None,
    ) -> None:
        self._repository = repository
        self._sonarr = sonarr_service = sonarr
        self._file_matcher = file_matcher
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
                    release.id,
                    export_failures_count=release.export_failures_count + 1
                )
                result.failed += 1

        return result

    async def _process_release(self, release: ReleaseRecord) -> None:
        # 1. Autocomplete mappings (local update + db update)
        updates = self._file_matcher.autocomplete(release.files)
        if updates:
            await self._repository.update_file_mappings(release.id, updates)
            # Apply updates locally so we can proceed without refetch
            file_map = {f.id: f for f in release.files}
            for update in updates:
                f = file_map.get(update.file_id)
                if f and update.mapping:
                    f.mapping = update.mapping

        # 2. Group files by Sonarr series ID
        # Map request_id -> sonarr_series_id
        requests_map = {r.id: r for r in release.requests}
        files_by_series: dict[int, list[ReleaseFileRecord]] = {}

        for file in release.files:
            if not file.mapping or not file.mapping.request_id:
                continue
            
            req = requests_map.get(file.mapping.request_id)
            if not req or not req.sonarr_series_id:
                continue
            
            files_by_series.setdefault(req.sonarr_series_id, []).append(file)

        # 3. Process each series
        all_import_files: list[ManualImportFile] = []
        
        for series_id, files in files_by_series.items():
            episodes = await self._sonarr.get_episodes(series_id)
            episode_map = {
                (ep.season_number, ep.episode_number): ep.id
                for ep in episodes
            }

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
                        path=file.path,
                        series_id=series_id,
                        episode_ids=[episode_id],
                        folder_name=release.name,
                    )
                )

        if not all_import_files:
            # Nothing to import, maybe mappings incomplete or already done?
            # If we matched nothing, maybe we shouldn't mark as exported?
            # Or if it's because files are extras (nfo, etc), we should.
            # For now, let's assume if we found NO importables but have files, we wait?
            # Or we mark success to avoid retry loop if there are simply no episodes matched.
            return

        # 4. Trigger import
        success = await self._sonarr.manual_import(all_import_files)
        
        if success:
            await self._repository.update_release(
                release.id,
                last_exported_info_hash=release.info_hash,
                export_failures_count=0,
            )
        else:
            raise RuntimeError("Sonarr manual import command failed") 
