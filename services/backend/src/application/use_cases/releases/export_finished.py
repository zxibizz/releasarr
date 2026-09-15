"""Use case for exporting finished releases back to Sonarr and Radarr."""

from __future__ import annotations

import posixpath
from dataclasses import dataclass, field
from datetime import UTC, datetime

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
from src.application.use_cases.requests.recompute_state import RecomputeRequestStateUseCase
from src.application.use_cases.requests.state import ArrCompletion
from src.core.logging import get_logger
from src.domain.enums import MediaType


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
        radarr: RadarrService,
        request_repository: MediaRequestRepository,
        recompute_state: RecomputeRequestStateUseCase,
        logger: Logger | None = None,
    ) -> None:
        self._repository = repository
        self._sonarr = sonarr
        self._radarr = radarr
        self._auto_mapper = auto_mapper
        self._download_service = download_service
        self._request_repository = request_repository
        self._recompute_state = recompute_state
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
                # Bound per request id because the request's activity view is built
                # from log records filtered on it.
                for request_id in release.request_ids or ["unknown"]:
                    self._logger.opt(exception=exc).error(
                        f"Failed to export release: {exc}",
                        request_id=request_id,
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
            for request_id in release.request_ids or ["unknown"]:
                self._logger.warning(
                    "Skipping export: download directory is unknown",
                    request_id=request_id,
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
        await self._record_exports(candidates, imported)

    def _has_exportable_files(
        self,
        release: ReleaseRecord,
        requests_map: dict[str, ReleaseRequestSnapshot],
    ) -> bool:
        return any(self._linked_request(file, requests_map) is not None for file in release.files)

    def _log_exported(self, release: ReleaseRecord, counts: dict[str, int], target: str) -> None:
        """Record one activity entry per request the import actually carried files for.

        Entries are bound per request id because the /logs endpoint filters on it,
        and a single release commonly spans several requests.
        """

        for request_id, count in counts.items():
            self._logger.info(
                f"Exported {count} file(s) to {target}",
                request_id=request_id,
                release_id=release.id,
                release_name=release.name,
                file_count=count,
            )

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

        files_by_series: dict[int, list[tuple[ReleaseFileRecord, str]]] = {}
        for file in release.files:
            request = self._linked_request(file, requests_map)
            if request is None or request.sonarr_series_id is None:
                continue
            if file.mapping and file.mapping.mapping_type is MediaType.MOVIE:
                continue
            files_by_series.setdefault(request.sonarr_series_id, []).append((file, request.id))

        if not files_by_series:
            return set()

        import_files: list[ManualImportFile] = []
        imported_seasons: set[tuple[int, int]] = set()
        exported_per_request: dict[str, int] = {}

        for series_id, files in files_by_series.items():
            episodes = await self._sonarr.get_episodes(series_id)
            episode_map = {(ep.season_number, ep.episode_number): ep.id for ep in episodes}

            for file, request_id in files:
                if not file.mapping or file.mapping.season is None or file.mapping.episode is None:
                    continue

                episode_id = episode_map.get((file.mapping.season, file.mapping.episode))
                if not episode_id:
                    self._logger.warning(
                        "Could not find Sonarr episode ID",
                        request_id=request_id,
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
                exported_per_request[request_id] = exported_per_request.get(request_id, 0) + 1

        if not import_files:
            return set()

        if not await self._sonarr.manual_import(import_files):
            raise RuntimeError("Sonarr manual import command failed")

        self._log_exported(release, exported_per_request, "Sonarr")
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

        import_files: list[MovieImportFile] = []
        imported_movies: set[int] = set()
        exported_per_request: dict[str, int] = {}

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
            exported_per_request[request.id] = exported_per_request.get(request.id, 0) + 1

        if not import_files:
            return set()

        if not await self._radarr.manual_import(import_files):
            raise RuntimeError("Radarr manual import command failed")

        self._log_exported(release, exported_per_request, "Radarr")
        return imported_movies

    async def _record_exports(
        self,
        candidates: list[ReleaseRequestSnapshot],
        imported: _Imported,
    ) -> None:
        """Stamp what the export landed on each request, then let the recompute settle it.

        Sonarr and Radarr are asked to confirm rather than assuming the import
        covered the request, since a release may only carry part of it; their
        answer is handed to `RecomputeRequestStateUseCase` as an `ArrCompletion`
        instead of writing `status` here directly, so completion has exactly one
        writer. The timestamp is recorded for every request the arr actually took
        files for, not just the ones that finished: a season a release only
        partly filled has still been exported. A movie has no partial state, so
        there Radarr's confirmation answers both questions at once.
        """

        details_by_series: dict[int, SeriesDetails] = {}
        exported_at = datetime.now(UTC)
        arr_completion: dict[str, ArrCompletion] = {}

        for request in candidates:
            if request.radarr_movie_id is not None:
                verdict = await self._movie_verdict(request, imported)
            else:
                verdict = await self._season_verdict(request, imported, details_by_series)
            if verdict is None:
                continue

            arr_completion[request.id] = verdict
            await self._request_repository.update_request(
                request.id,
                UpdateMediaRequestData(exported_at=exported_at),
            )

            if verdict.is_complete:
                self._logger.info(
                    "Marked request as completed",
                    request_id=request.id,
                    sonarr_series_id=request.sonarr_series_id,
                    radarr_movie_id=request.radarr_movie_id,
                    season_number=request.season_number,
                )

        if arr_completion:
            await self._recompute_state.execute(
                list(arr_completion.keys()), arr_completion=arr_completion
            )

    async def _season_verdict(
        self,
        request: ReleaseRequestSnapshot,
        imported: _Imported,
        details_by_series: dict[int, SeriesDetails],
    ) -> ArrCompletion | None:
        """Sonarr's verdict on this request's season, or None if untouched by this export."""

        if not _season_was_imported(request, imported):
            return None
        series_id = request.sonarr_series_id
        season_number = request.season_number
        if series_id is None or season_number is None:
            return None

        details = details_by_series.get(series_id)
        if details is None:
            details = await self._sonarr.get_series(series_id)
            details_by_series[series_id] = details

        season = details.seasons.get(season_number)
        if season is None:
            return ArrCompletion(is_complete=False)

        is_complete = (
            bool(season.episode_count) and season.episode_file_count >= season.episode_count
        )
        has_unaired = season.episode_count < season.total_episode_count
        return ArrCompletion(is_complete=is_complete, has_unaired=has_unaired)

    async def _movie_verdict(
        self,
        request: ReleaseRequestSnapshot,
        imported: _Imported,
    ) -> ArrCompletion | None:
        """Radarr's verdict on this request's movie, or None if untouched by this export.

        A movie has no partial state, so an import Radarr took but does not yet
        report a file for is not treated as a verdict at all - the next export
        run gets another chance rather than the request being reopened on a
        guess.
        """

        movie_id = request.radarr_movie_id
        if movie_id is None or movie_id not in imported.movies:
            return None
        if not (await self._radarr.get_movie(movie_id)).has_file:
            return None
        return ArrCompletion(is_complete=True)


def _season_was_imported(
    request: ReleaseRequestSnapshot,
    imported: _Imported,
) -> bool:
    """Whether Sonarr accepted any file for this request's season in this export."""

    if request.sonarr_series_id is None or request.season_number is None:
        return False
    return (request.sonarr_series_id, request.season_number) in imported.seasons


__all__ = ["ExportFinishedReleasesUseCase", "ExportFinishedResult"]
