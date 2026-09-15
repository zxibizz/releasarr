"""Checking a release against its indexer, and re-downloading it when it moved.

Shared by the scheduled re-grab sweep and the on-demand refresh on a request, so
the two cannot drift on what counts as outdated, on the warnings they leave
behind, or on what they log against the request.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlparse

from torrentool.api import Torrent

from src.application.interfaces.indexers import IndexerDirectory, IndexerRecord
from src.application.interfaces.releases import (
    MANUAL_SOURCE,
    FileReconciliation,
    ReleaseDownloadService,
    ReleaseFileRecord,
    ReleaseRecord,
    ReleaseRepository,
    ReleaseSearchResultRecord,
    ReleaseSearchService,
    ReleaseSearchUnavailableError,
)
from src.application.interfaces.request_warnings import (
    RequestWarningRecord,
    RequestWarningRepository,
)
from src.application.use_cases.indexers.list_indexers import derive_health
from src.application.use_cases.releases.auto_mapping import ReleaseAutoMapper
from src.application.use_cases.releases.exceptions import ReleaseRegrabRejectedError
from src.application.use_cases.releases.grab import to_release_files
from src.application.use_cases.requests.recompute_state import RecomputeRequestStateUseCase
from src.application.utility.torrent import parse_torrent
from src.application.utility.torrent_files import reconcile_release_files
from src.core.logging import get_logger
from src.domain.enums import IndexerHealth, ReleaseStatus, RequestWarningCode

if TYPE_CHECKING:
    from loguru import Logger


def is_regrabbable(release: ReleaseRecord) -> bool:
    """Whether an indexer can still be asked about this release.

    A hand-supplied torrent has no indexer to go back to and can never be found
    again, which is why the sweep filters those out in SQL as well.
    """

    return release.torrent_source is not None and release.torrent_source != MANUAL_SOURCE


class ReleaseRegrapper:
    """Looks releases up again on their own indexer and re-downloads replaced torrents.

    The check is a search for the release's own name, scoped to the indexer it
    came from, followed by a comparison of info hashes: an indexer that replaced
    a torrent (a repack) serves the same release id under a new hash.

    The replacement's file list is read before it is queued, because the release
    row it rewrites is the one holding the mappings the export imports by. Files
    the release already had keep their mappings, files the replacement adds are
    automapped on their own, and a replacement that dropped one of them is
    refused rather than left describing a file that is no longer there.
    """

    def __init__(
        self,
        repository: ReleaseRepository,
        search_service: ReleaseSearchService,
        download_service: ReleaseDownloadService,
        auto_mapper: ReleaseAutoMapper,
        warning_repository: RequestWarningRepository,
        recompute_state: RecomputeRequestStateUseCase,
        directory: IndexerDirectory,
        logger: Logger | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._search_service = search_service
        self._download_service = download_service
        self._auto_mapper = auto_mapper
        self._directory = directory
        self._warning_repository = warning_repository
        self._recompute_state = recompute_state
        self._logger = logger or get_logger(component="regrab_releases")
        self._clock = clock or (lambda: datetime.now(UTC))

    async def indexers_by_name(self) -> dict[str, IndexerRecord]:
        """Map a release's stored indexer name back to Prowlarr's own record.

        Best-effort: a release older than the indexer list, or Prowlarr being
        briefly unreachable, should not stop every re-grab check from running -
        it just falls back to the unscoped search for that release.
        """

        if not self._directory.is_configured:
            return {}
        try:
            indexers = await self._directory.list_indexers()
        except Exception as exc:
            self._logger.warning("Failed to list indexers for regrab scoping", error=str(exc))
            return {}
        return {indexer.name.lower(): indexer for indexer in indexers}

    def _log_for_requests(
        self,
        log: Callable[..., None],
        message: str,
        release: ReleaseRecord,
        **fields: object,
    ) -> None:
        """Record one line per request holding this release.

        A request's activity view is built by filtering the log file on
        `request_id`, so a line that names only the release is reachable from the
        logs page but invisible on every request it belongs to. A release shared
        by several requests is why this is a loop rather than one call.
        """

        for request_id in release.request_ids or ["unknown"]:
            log(message, request_id=request_id, release_id=release.id, **fields)

    async def regrab(
        self, release: ReleaseRecord, indexers_by_name: dict[str, IndexerRecord]
    ) -> bool:
        """Check one release, re-downloading it when the indexer replaced it.

        Returns whether a new download was queued. Every way out of here logs
        against the release's requests: a check that found nothing to do is still
        the answer to "what happened to this request", and the sweep runs hourly
        over releases nobody is watching.
        """

        # Search Prowlarr for the specific release, scoped to the indexer it
        # originally came from when that indexer is still known to Prowlarr.
        # We rely on the release name (torrent name) to find it again.
        indexer = (
            indexers_by_name.get(release.torrent_source.lower()) if release.torrent_source else None
        )

        unusable = self._unusable_reason(indexer)
        if unusable is not None:
            # Prowlarr will refuse the query either way, so spending the timeout
            # budget on it only delays the rest of the sweep.
            self._log_for_requests(
                self._logger.warning,
                "Could not check for updates: indexer unusable",
                release,
                release_name=release.name,
                indexer=release.torrent_source,
                reason=unusable,
            )
            await self._write_regrab_warning(release, reason=unusable)
            return False

        indexer_id = indexer.indexer_id if indexer is not None else None
        try:
            results = await self._search_service.search(release.name, indexer_id=indexer_id)
        except ReleaseSearchUnavailableError as exc:
            # An indexer that is banned or not responding is an expected, transient
            # condition rather than a bug, but the request it would have updated is
            # left stale, which is worth surfacing on that request's activity log.
            self._log_for_requests(
                self._logger.warning,
                "Could not check for updates: indexer unavailable",
                release,
                release_name=release.name,
                error=str(exc),
            )
            await self._write_regrab_warning(release, reason=str(exc))
            return False

        await self._write_regrab_warning(release, reason=None)

        # Find the result that matches our current GUID (Release.id)
        match = next((r for r in results.results if r.release_id == release.id), None)
        if not match:
            # The indexer dropped the release or reissued it under another id, so
            # there is no torrent left to compare hashes against.
            self._log_for_requests(
                self._logger.info,
                "Release is no longer listed by its indexer",
                release,
                release_name=release.name,
                indexer=release.torrent_source,
            )
            await self._write_not_listed_warning(release, indexer=release.torrent_source)
            return False

        # The release is still listed, so a row an earlier check left behind is
        # cleared here rather than on any valid response: an indexer that
        # answered without knowing this release is exactly what set it.
        await self._write_not_listed_warning(release, indexer=None)

        new_hash: str | None = None
        torrent_bytes: bytes | None = None

        # distinct source logic
        if match.magnet_link:
            new_hash = self._extract_hash_from_magnet(match.magnet_link)

        if not new_hash and match.torrent_file_url:
            try:
                torrent_bytes = await self._search_service.fetch_torrent(match.torrent_file_url)
                torrent = Torrent.from_string(torrent_bytes)
                new_hash = torrent.info_hash
            except Exception as exc:
                self._log_for_requests(
                    self._logger.warning,
                    "Failed to fetch/parse torrent file",
                    release,
                    release_name=release.name,
                    error=str(exc),
                )
                return False

        if not new_hash:
            # Neither link the indexer reported yielded a hash, so there is nothing
            # to compare against and the release cannot be called outdated.
            self._log_for_requests(
                self._logger.warning,
                "Could not read the release's info hash",
                release,
                release_name=release.name,
                indexer=release.torrent_source,
            )
            return False

        # Compare hashes (case insensitive)
        current_hash = release.info_hash
        if new_hash.upper() == current_hash.upper():
            self._log_for_requests(
                self._logger.info,
                "Release is up to date on its indexer",
                release,
                release_name=release.name,
                indexer=release.torrent_source,
                info_hash=current_hash,
            )
            return False

        request_ids = release.request_ids or ["unknown"]

        # The replacement is about to be written over a row whose files describe
        # the torrent it is replacing, so its own file list is read first - and a
        # torrent that dropped a file the release already has is refused before
        # anything is queued. A list that cannot be read is not refused: a magnet
        # only result is a normal indexer answer, it just cannot be reconciled.
        replacement_files = await self._read_replacement_files(release, match, torrent_bytes)
        reconciliation: FileReconciliation | None = None
        if replacement_files is not None:
            reconciliation = reconcile_release_files(release.files, replacement_files)
            if reconciliation.missing:
                await self._refuse_missing_files(release, reconciliation.missing)
            await self._write_files_missing_warning(release, missing_files=None)

        await self._download_service.queue_download(
            request_id=request_ids[0],
            release_id=release.id,
            magnet_link=match.magnet_link or "",
            torrent_bytes=torrent_bytes,
        )

        # Update DB
        await self._repository.update_release(
            release.id,
            info_hash=new_hash.upper(),
            export_failures_count=0,
            last_exported_info_hash=None,  # Reset export
            name=match.release_name,  # Update name in case of rename
            info_url=match.info_url,
            published_at=match.publish_date,
            # The replacement is the same release downloaded again, so the row
            # cannot go on calling itself finished: `completed` is what the export
            # queue imports from, and the files are being replaced underneath it.
            # Reading the client back is what settles the real status, so this is
            # only the state the queued download starts in.
            status=ReleaseStatus.DOWNLOADING,
            progress=0.0,
            completed_at=None,
        )

        if reconciliation is not None:
            await self._settle_files(release, reconciliation)

        self._log_for_requests(
            self._logger.info,
            "Re-grabbed updated release",
            release,
            release_name=match.release_name,
            indexer=release.torrent_source,
            old_hash=current_hash,
            new_hash=new_hash.upper(),
        )

        try:
            # The new torrent is back in flight and `published_at` just
            # moved, so the request must leave `monitoring` immediately
            # rather than wait for the next release sync.
            await self._recompute_state.execute(request_ids)
        except Exception as exc:  # pragma: no cover - defensive
            self._log_for_requests(
                self._logger.warning,
                "Failed to settle requests after a re-grab",
                release,
                error=str(exc),
            )

        return True

    async def _read_replacement_files(
        self,
        release: ReleaseRecord,
        match: ReleaseSearchResultRecord,
        torrent_bytes: bytes | None,
    ) -> list[ReleaseFileRecord] | None:
        """Read the replacement torrent's file list, or None when there is none.

        Only a ``.torrent`` carries a file list, and the hash comparison has
        already been made out of whatever the indexer offered, so this is the one
        place that fetches it. What it returns is for the file check alone: the
        download still goes out as whatever the search result carried, so the
        client receives the same torrent the recorded hash names.

        Failing is not an error the re-grab should die on - an unusable torrent
        file still leaves a magnet to download, and the log line is what tells
        "nothing to compare" apart from "compared, all clear".
        """

        if torrent_bytes is None and match.torrent_file_url:
            try:
                torrent_bytes = await self._search_service.fetch_torrent(match.torrent_file_url)
            except Exception as exc:
                self._log_for_requests(
                    self._logger.warning,
                    "Could not read the replacement torrent's file list",
                    release,
                    release_name=release.name,
                    error=str(exc),
                )
                return None

        if not torrent_bytes:
            return None

        try:
            torrent = parse_torrent(torrent_bytes)
        except ValueError as exc:
            self._log_for_requests(
                self._logger.warning,
                "Could not read the replacement torrent's file list",
                release,
                release_name=release.name,
                error=str(exc),
            )
            return None

        return to_release_files(torrent.files) or None

    async def _refuse_missing_files(
        self,
        release: ReleaseRecord,
        missing: Sequence[ReleaseFileRecord],
    ) -> None:
        """Abandon the re-grab over files the replacement torrent does not carry.

        A release keeps one row per torrent, and an export imports by the paths on
        it, so a replacement that drops a file would leave that row pointing at
        something that was never downloaded. Nothing has been queued or written at
        this point, which is what makes refusing cheap.
        """

        names = [record.name for record in missing]
        self._log_for_requests(
            self._logger.error,
            "Replacement torrent is missing files the release already has",
            release,
            release_name=release.name,
            missing_file_count=len(names),
            missing_files=names,
        )
        await self._write_files_missing_warning(release, missing_files=names)
        raise ReleaseRegrabRejectedError(release.id, names)

    async def _settle_files(
        self,
        release: ReleaseRecord,
        reconciliation: FileReconciliation,
    ) -> None:
        """Record the replacement's files and automap only the ones it added.

        Everything the release already carried was resolved once - by hand or by
        the grab - and re-deriving those mappings is how a correction gets lost,
        so the matcher is only allowed to speak for the files that are new here.
        """

        try:
            merged = await self._repository.sync_release_files(release.id, reconciliation)
        except Exception as exc:  # pragma: no cover - defensive
            self._log_for_requests(
                self._logger.warning,
                "Failed to record the replacement torrent's files",
                release,
                error=str(exc),
            )
            return

        if merged is None:
            return

        added_ids = [record.id for record in reconciliation.added]
        mapped = 0
        if added_ids:
            try:
                mapped = await self._auto_mapper.apply_to(replace(release, files=merged), added_ids)
            except Exception as exc:  # pragma: no cover - defensive
                self._log_for_requests(
                    self._logger.warning,
                    "Failed to automap the replacement torrent's new files",
                    release,
                    error=str(exc),
                )
                return

        self._log_for_requests(
            self._logger.info,
            "Recorded the replacement torrent's files",
            release,
            file_count=len(merged),
            added_file_count=len(added_ids),
            mapped_file_count=mapped,
        )

        # Only a release that gained files nobody could place needs a human; one
        # whose new files mapped, or which gained none, is exactly what a re-grab
        # is supposed to look like.
        await self._write_files_unmapped_warning(
            release,
            file_ids=added_ids if added_ids and not mapped else None,
        )

    def _unusable_reason(self, indexer: IndexerRecord | None) -> str | None:
        """Why this indexer cannot answer a search right now, or None if it can.

        An unknown indexer is not reported: the search falls back to Prowlarr's
        unscoped sweep, which may still find the release elsewhere.
        """

        if indexer is None:
            return None
        health = derive_health(indexer, self._clock())
        if health is IndexerHealth.DISABLED:
            return f"indexer {indexer.name} is disabled in Prowlarr"
        if health is IndexerHealth.BLOCKED:
            return f"indexer {indexer.name} is blocked by Prowlarr until {indexer.disabled_till}"
        if not indexer.supports_search:
            return f"indexer {indexer.name} does not support search"
        return None

    async def _write_regrab_warning(self, release: ReleaseRecord, reason: str | None) -> None:
        """Record or clear `REGRAB_INDEXER_UNAVAILABLE` for this release alone.

        Scoped to the release, not the request: a request with several
        releases must not have a sibling's fresh failure wiped out just
        because this release's own check came back clean.
        """

        rows = (
            []
            if reason is None
            else [
                RequestWarningRecord(
                    request_id=request_id,
                    release_id=release.id,
                    code=RequestWarningCode.REGRAB_INDEXER_UNAVAILABLE,
                    details={"reason": reason},
                )
                for request_id in release.request_ids
            ]
        )
        try:
            await self._warning_repository.replace_for_releases(
                RequestWarningCode.REGRAB_INDEXER_UNAVAILABLE, [release.id], rows
            )
        except Exception as exc:  # pragma: no cover - defensive
            self._log_for_requests(
                self._logger.warning,
                "Failed to persist regrab indexer-unavailable warning",
                release,
                error=str(exc),
            )

    async def _write_not_listed_warning(self, release: ReleaseRecord, indexer: str | None) -> None:
        """Record or clear `RELEASE_NOT_LISTED` for this release alone.

        Overloading `indexer` with None to mean "clear" mirrors
        `_write_regrab_warning`, and is only safe because the two callers sit on
        either side of the match test: the release is guaranteed to carry a
        `torrent_source`, since releases without one are never checked.

        The code is deliberately not cleared on every valid search response the
        way `REGRAB_INDEXER_UNAVAILABLE` is: an indexer answering without this
        release is precisely the condition, so only finding it again resolves
        it.
        """

        rows = (
            []
            if indexer is None
            else [
                RequestWarningRecord(
                    request_id=request_id,
                    release_id=release.id,
                    code=RequestWarningCode.RELEASE_NOT_LISTED,
                    details={"indexer": indexer},
                )
                for request_id in release.request_ids
            ]
        )
        try:
            await self._warning_repository.replace_for_releases(
                RequestWarningCode.RELEASE_NOT_LISTED, [release.id], rows
            )
        except Exception as exc:  # pragma: no cover - defensive
            self._log_for_requests(
                self._logger.warning,
                "Failed to persist release-not-listed warning",
                release,
                error=str(exc),
            )

    async def _write_files_missing_warning(
        self, release: ReleaseRecord, missing_files: list[str] | None
    ) -> None:
        """Record or clear `REGRAB_FILES_MISSING` for this release alone.

        Set by the refusal that stops a replacement from being grabbed and cleared
        by a later check whose replacement does carry every stored file. Only a
        readable file list can tell it is resolved, so a check that could not read
        one leaves the row exactly where it was.
        """

        details = (
            {"missing_files": missing_files, "file_count": len(missing_files)}
            if missing_files
            else None
        )
        rows = (
            [
                RequestWarningRecord(
                    request_id=request_id,
                    release_id=release.id,
                    code=RequestWarningCode.REGRAB_FILES_MISSING,
                    details=details,
                )
                for request_id in release.request_ids
            ]
            if details is not None
            else []
        )
        try:
            await self._warning_repository.replace_for_releases(
                RequestWarningCode.REGRAB_FILES_MISSING, [release.id], rows
            )
        except Exception as exc:  # pragma: no cover - defensive
            self._log_for_requests(
                self._logger.warning,
                "Failed to persist regrab missing-files warning",
                release,
                error=str(exc),
            )

    async def _write_files_unmapped_warning(
        self, release: ReleaseRecord, file_ids: list[str] | None
    ) -> None:
        """Record or clear `REGRAB_FILES_UNMAPPED` for this release alone.

        The ids are kept in `details` rather than left implied: they are what
        tells a later save of the mappings whether the files this warning named
        have since been placed, which is how it stops asking for a human nobody
        still needs.
        """

        details = {"file_ids": file_ids, "file_count": len(file_ids)} if file_ids else None
        rows = (
            [
                RequestWarningRecord(
                    request_id=request_id,
                    release_id=release.id,
                    code=RequestWarningCode.REGRAB_FILES_UNMAPPED,
                    details=details,
                )
                for request_id in release.request_ids
            ]
            if details is not None
            else []
        )
        try:
            await self._warning_repository.replace_for_releases(
                RequestWarningCode.REGRAB_FILES_UNMAPPED, [release.id], rows
            )
        except Exception as exc:  # pragma: no cover - defensive
            self._log_for_requests(
                self._logger.warning,
                "Failed to persist regrab unmapped-files warning",
                release,
                error=str(exc),
            )

    @staticmethod
    def _extract_hash_from_magnet(magnet_link: str) -> str | None:
        try:
            parsed = urlparse(magnet_link)
            if parsed.scheme != "magnet":
                return None
            params = parse_qs(parsed.query)
            xt_values = params.get("xt", [])
            for value in xt_values:
                if value.startswith("urn:btih:"):
                    return value.split(":")[-1].upper()
        except Exception:
            return None
        return None


__all__ = ["ReleaseRegrapper", "is_regrabbable"]
