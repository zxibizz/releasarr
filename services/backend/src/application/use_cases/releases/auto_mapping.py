"""Automatic mapping of release files onto the requests they satisfy."""

from __future__ import annotations

from collections.abc import Collection

from loguru._logger import Logger

from src.application.interfaces.media_requests import MediaRequestRecord, MediaRequestRepository
from src.application.interfaces.releases import (
    FileMappingUpdateData,
    ReleaseRecord,
    ReleaseRepository,
    ReleaseRequestSnapshot,
)
from src.application.utility.file_matcher import ReleaseFileMatcher
from src.core.logging import get_logger
from src.domain.enums import MediaType


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
        request_repository: MediaRequestRepository,
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

        updates, candidates = await self.suggest(release)
        if updates:
            await self._repository.update_file_mappings(release.id, updates)
            self._log_auto_mapped(release, updates)
        return candidates

    async def apply_to(self, release: ReleaseRecord, file_ids: Collection[str]) -> int:
        """Map only the given files, returning how many mappings were written.

        Used after a re-grab, where the files the replacement torrent added are
        the only ones automapping may speak for: everything else was already
        resolved, by hand or by an earlier pass, and a replacement torrent is not
        a reason to revisit it. The matcher still sees the whole file list, since
        its numbering and its movie pass both read it.
        """

        scoped = set(file_ids)
        if not scoped:
            return 0

        updates, _ = await self.suggest(release)
        updates = [update for update in updates if update.file_id in scoped]
        if not updates:
            return 0

        await self._repository.update_file_mappings(release.id, updates)
        self._log_auto_mapped(release, updates)
        return len(updates)

    def _log_auto_mapped(
        self, release: ReleaseRecord, updates: list[FileMappingUpdateData]
    ) -> None:
        """Record one activity entry per request the mapping pass resolved files for.

        Entries are bound per request id because the /logs endpoint filters on it,
        and a pack routinely resolves onto several requests in one pass.
        """

        mapped_per_request: dict[str, int] = {}
        for update in updates:
            request_id = update.mapping.request_id if update.mapping else None
            if not request_id:
                continue
            mapped_per_request[request_id] = mapped_per_request.get(request_id, 0) + 1

        for request_id, count in mapped_per_request.items():
            self._logger.info(
                f"Auto-mapped {count} release file(s) to this request",
                request_id=request_id,
                release_id=release.id,
                release_name=release.name,
                file_count=count,
            )

    async def suggest(
        self,
        release: ReleaseRecord,
    ) -> tuple[list[FileMappingUpdateData], list[ReleaseRequestSnapshot]]:
        """Work out the mappings and the requests considered, storing neither.

        The matcher writes each mapping onto the file record as it goes, so the
        records handed in come back carrying the proposals. Callers that only
        want to offer them must pass records they own: the repository builds a
        fresh set on every read, so anything loaded for this call qualifies.
        """

        candidates = await self.candidate_requests(release)
        return self._file_matcher.autocomplete(release.files, candidates), candidates

    async def candidate_requests(self, release: ReleaseRecord) -> list[ReleaseRequestSnapshot]:
        """Return the requests a release's files may map to.

        A pack is normally grabbed from a single request, so its siblings are
        pulled in as well: the other seasons of the same Sonarr series, or the
        other outstanding Radarr movies a collection may cover.
        """

        candidates = {request.id: request for request in release.requests}
        await self._add_sibling_seasons(release, candidates)
        await self._add_sibling_movies(release, candidates)
        return list(candidates.values())

    async def _add_sibling_seasons(
        self,
        release: ReleaseRecord,
        candidates: dict[str, ReleaseRequestSnapshot],
    ) -> None:
        series_ids = {
            request.sonarr_series_id
            for request in release.requests
            if request.sonarr_series_id is not None
        }
        if not series_ids:
            return

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
                candidates[record.id] = self._to_snapshot(record)

    async def _add_sibling_movies(
        self,
        release: ReleaseRecord,
        candidates: dict[str, ReleaseRequestSnapshot],
    ) -> None:
        """Offer the other outstanding movies to a release that grabbed one.

        A collection pack is grabbed from whichever movie was wanted, and the
        rest of it only maps if their requests are on the table too. There is no
        collection link to follow, so every movie Radarr still wants is offered
        and the matcher decides on the file names.
        """

        if not any(request.media_type is MediaType.MOVIE for request in release.requests):
            return

        for record in await self._request_repository.list_radarr_requests():
            if record.id in candidates:
                continue
            candidates[record.id] = self._to_snapshot(record)

    def _to_snapshot(self, record: MediaRequestRecord) -> ReleaseRequestSnapshot:
        return ReleaseRequestSnapshot(
            id=record.id,
            sonarr_series_id=record.sonarr_series_id,
            title=record.title,
            media_type=record.media_type,
            season_number=record.season_number,
            radarr_movie_id=record.radarr_movie_id,
            year=record.year,
            alternate_titles=_alternate_titles(record),
        )


def _alternate_titles(record: MediaRequestRecord) -> list[str]:
    """Every other name the request is known by, for matching release names."""

    titles: list[str] = []
    for localization in record.localizations.values():
        if localization.title and localization.title != record.title:
            titles.append(localization.title)
    if record.series_title and record.series_title != record.title:
        titles.append(record.series_title)
    return titles


__all__ = ["ReleaseAutoMapper"]
