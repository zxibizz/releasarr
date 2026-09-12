"""Use case for exporting finished releases back to Sonarr and Radarr."""

from __future__ import annotations

import posixpath
from dataclasses import dataclass, field

from loguru._logger import Logger

from src.application.interfaces.media_requests import (
    MediaRequestRepository,
    UpdateMediaRequestData,
)
from src.application.interfaces.radarr import MovieImportFile, RadarrService
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
from src.domain.enums import MediaRequestStatus, MediaType


@dataclass(slots=True)
class ExportFinishedResult:
    """Result summary for the export operation."""

    succeeded: int = 0
    failed: int = 0


@dataclass(slots=True)
class _Imported:
    """What each backend actually took, so requests can be closed against it."""

    seasons: set[tuple[int, int]] = field(default_factory=set)
    movies: set[int] = field(default_factory=set)

    def __bool__(self) -> bool:
        return bool(self.seasons or self.movies)


class ExportFinishedReleasesUseCase:
    """Orchestrate the export of completed downloads to Sonarr and Radarr."""

    def __init__(
        self,
        repository: ReleaseRepository,
        sonarr: SonarrService,
        auto_mapper: ReleaseAutoMapper,
        download_service: ReleaseDownloadService,
        radarr: RadarrService | None = None,
        request_repository: MediaRequestRepository | None = None,
        logger: Logger | None = None,
    ) -> None:
        self._repository = repository
        self._sonarr = sonarr
        self._radarr = radarr
        self._auto_mapper = auto_mapper
        self._download_service = download_service
        self._request_repository = request_repository
        self._logger = logger or get_logger(component="export_finished_releases")

    async def execute(self) -> ExportFinishedResult:
        """Process all finished but not yet exported releases."""

        releases = await self._repository.get_finished_not_exported()
        result = ExportFinishedResult()

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
        requests_map = {request.id: request for request in candidates}

        # 2. Resolve where the download client put the payload. Sonarr and Radarr
        # read the files off the same filesystem, so they need absolute paths.
        # Nothing is fetched until a file is actually mapped to something.
        if not self._has_exportable_files(release, requests_map):
            return

        download_dir = await self._download_service.get_download_directory(release.info_hash)
        if not download_dir:
            self._logger.warning(
                "Skipping export: download directory is unknown",
                release_id=release.id,
                release_name=release.name,
                info_hash=release.info_hash,
            )
            return

        # 3. Hand each media type to the app that owns it
        imported = _Imported()
        imported.seasons = await self._export_series(release, requests_map, download_dir)
        imported.movies = await self._export_movies(release, requests_map, download_dir)

        if not imported:
            # Nothing resolvable yet: leave the release unexported so a later run
            # can retry once mappings or metadata catch up.
            return

        await self._repository.update_release(
            release.id,
            last_exported_info_hash=release.info_hash,
            export_failures_count=0,
        )
        await self._complete_requests(candidates, imported)

    def _has_exportable_files(
        self,
        release: ReleaseRecord,
        requests_map: dict[str, ReleaseRequestSnapshot],
    ) -> bool:
        return any(self._linked_request(file, requests_map) is not None for file in release.files)

    def _linked_request(
        self,
        file: ReleaseFileRecord,
        requests_map: dict[str, ReleaseRequestSnapshot],
    ) -> ReleaseRequestSnapshot | None:
        if not file.mapping or not file.mapping.request_id:
            return None
        request = requests_map.get(file.mapping.request_id)
        if request is None:
            return None
        if request.sonarr_series_id is None and request.radarr_movie_id is None:
            return None
        return request

    async def _export_series(
        self,
        release: ReleaseRecord,
        requests_map: dict[str, ReleaseRequestSnapshot],
        download_dir: str,
    ) -> set[tuple[int, int]]:
        """Import the release's episode files into Sonarr."""

        files_by_series: dict[int, list[ReleaseFileRecord]] = {}
        for file in release.files:
            request = self._linked_request(file, requests_map)
            if request is None or request.sonarr_series_id is None:
                continue
            if file.mapping and file.mapping.mapping_type is MediaType.MOVIE:
                continue
            files_by_series.setdefault(request.sonarr_series_id, []).append(file)

        if not files_by_series:
            return set()

        import_files: list[ManualImportFile] = []
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

                import_files.append(
                    ManualImportFile(
                        path=posixpath.join(download_dir, file.path),
                        series_id=series_id,
                        episode_ids=[episode_id],
                        folder_name=release.name,
                    )
                )
                imported_seasons.add((series_id, file.mapping.season))

        if not import_files:
            return set()

        if not await self._sonarr.manual_import(import_files):
            raise RuntimeError("Sonarr manual import command failed")

        return imported_seasons

    async def _export_movies(
        self,
        release: ReleaseRecord,
        requests_map: dict[str, ReleaseRequestSnapshot],
        download_dir: str,
    ) -> set[int]:
        """Import the release's movie files into Radarr.

        Radarr resolves the file against the movie itself, so unlike the series
        path there is no per-episode lookup to do first.
        """

        if self._radarr is None:
            return set()

        import_files: list[MovieImportFile] = []
        imported_movies: set[int] = set()

        for file in release.files:
            request = self._linked_request(file, requests_map)
            if request is None or request.radarr_movie_id is None:
                continue
            if not file.mapping or file.mapping.mapping_type is not MediaType.MOVIE:
                continue

            import_files.append(
                MovieImportFile(
                    path=posixpath.join(download_dir, file.path),
                    movie_id=request.radarr_movie_id,
                    folder_name=release.name,
                )
            )
            imported_movies.add(request.radarr_movie_id)

        if not import_files:
            return set()

        if not await self._radarr.manual_import(import_files):
            raise RuntimeError("Radarr manual import command failed")

        return imported_movies

    async def _complete_requests(
        self,
        candidates: list[ReleaseRequestSnapshot],
        imported: _Imported,
    ) -> None:
        """Close the requests Sonarr and Radarr now hold in full.

        The Sonarr and Radarr syncs own this transition everywhere else, but the
        sequence a finished download runs deliberately leaves those tasks out, so
        a request would otherwise stay in flight until the next hourly sync. Both
        apps are still asked to confirm rather than assuming the import covered
        the request, since a release may only carry part of it.
        """

        if self._request_repository is None:
            return

        details_by_series: dict[int, SeriesDetails] = {}

        for request in candidates:
            if request.radarr_movie_id is not None:
                if not await self._movie_is_complete(request, imported):
                    continue
            elif not await self._season_is_complete(request, imported, details_by_series):
                continue

            await self._request_repository.update_request(
                request.id,
                UpdateMediaRequestData(status=MediaRequestStatus.COMPLETED),
            )
            self._logger.info(
                "Marked request as completed",
                request_id=request.id,
                sonarr_series_id=request.sonarr_series_id,
                radarr_movie_id=request.radarr_movie_id,
                season_number=request.season_number,
            )

    async def _season_is_complete(
        self,
        request: ReleaseRequestSnapshot,
        imported: _Imported,
        details_by_series: dict[int, SeriesDetails],
    ) -> bool:
        series_id = request.sonarr_series_id
        season_number = request.season_number
        if series_id is None or season_number is None:
            return False
        if (series_id, season_number) not in imported.seasons:
            return False

        details = details_by_series.get(series_id)
        if details is None:
            details = await self._sonarr.get_series(series_id)
            details_by_series[series_id] = details

        season = details.seasons.get(season_number)
        if season is None or not season.episode_count:
            return False
        return season.episode_file_count >= season.episode_count

    async def _movie_is_complete(
        self,
        request: ReleaseRequestSnapshot,
        imported: _Imported,
    ) -> bool:
        movie_id = request.radarr_movie_id
        if self._radarr is None or movie_id is None:
            return False
        if movie_id not in imported.movies:
            return False
        return (await self._radarr.get_movie(movie_id)).has_file


__all__ = ["ExportFinishedReleasesUseCase", "ExportFinishedResult"]
