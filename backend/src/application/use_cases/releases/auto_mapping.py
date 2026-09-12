"""Automatic mapping of release files onto the requests they satisfy."""

from __future__ import annotations

from loguru._logger import Logger

from src.application.interfaces.media_requests import MediaRequestRepository
from src.application.interfaces.releases import (
    ReleaseRecord,
    ReleaseRepository,
    ReleaseRequestSnapshot,
)
from src.application.utility.file_matcher import ReleaseFileMatcher
from src.core.logging import get_logger


class ReleaseAutoMapper:
    """Resolve and persist the mappings of a release's files.

    Runs both when a release is grabbed and again before it is exported: the grab
    gives the user something to review straight away, while the export pass
    re-runs against the requests that exist by then.
    """

    def __init__(
        self,
        repository: ReleaseRepository,
        file_matcher: ReleaseFileMatcher,
        request_repository: MediaRequestRepository | None = None,
        logger: Logger | None = None,
    ) -> None:
        self._repository = repository
        self._file_matcher = file_matcher
        self._request_repository = request_repository
        self._logger = logger or get_logger(component="release_auto_mapping")

    async def apply(self, release: ReleaseRecord) -> list[ReleaseRequestSnapshot]:
        """Map what can be mapped and return the requests considered.

        Mappings set by hand are preserved by the matcher, so this is safe to run
        repeatedly over the lifetime of a release.
        """

        candidates = await self.candidate_requests(release)
        updates = self._file_matcher.autocomplete(release.files, candidates)
        if updates:
            await self._repository.update_file_mappings(release.id, updates)
            self._logger.info(
                "Auto-mapped release files",
                release_id=release.id,
                release_name=release.name,
                mapped_files=len(updates),
            )
        return candidates

    async def candidate_requests(self, release: ReleaseRecord) -> list[ReleaseRequestSnapshot]:
        """Return the requests a release's files may map to.

        A multi-season pack is normally grabbed from a single season's request, so the
        sibling season requests of the same Sonarr series are pulled in as well.
        """

        candidates = {request.id: request for request in release.requests}
        if self._request_repository is None:
            return list(candidates.values())

        series_ids = {
            request.sonarr_series_id
            for request in release.requests
            if request.sonarr_series_id is not None
        }
        if not series_ids:
            return list(candidates.values())

        covered = {
            request.season_number
            for request in release.requests
            if request.season_number is not None
        }
        missing = self._file_matcher.seasons_in(release.files) - covered

        for series_id in sorted(series_ids):
            for season in sorted(missing):
                record = await self._request_repository.find_by_sonarr(
                    sonarr_series_id=series_id,
                    season_number=season,
                )
                if record is None or record.id in candidates:
                    continue
                candidates[record.id] = ReleaseRequestSnapshot(
                    id=record.id,
                    sonarr_series_id=record.sonarr_series_id,
                    title=record.title,
                    media_type=record.media_type,
                    season_number=record.season_number,
                )

        return list(candidates.values())


__all__ = ["ReleaseAutoMapper"]
