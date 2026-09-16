"""Derive a media request's status and freshness from its releases.

The rules here used to live inline in `tasks/sync_releases.py`, mutating the ORM
directly and skipping every request without a release. Extracting them as a pure
function lets every release-lifecycle use case share the same derivation instead
of waiting for the next scheduled sync.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from src.application.interfaces.media_requests import MediaRequestRecord
from src.application.interfaces.releases import MANUAL_SOURCE, ReleaseRecord
from src.application.interfaces.sonarr import SeriesSeasonDetails
from src.application.utility.sentinels import UNSET, _Unset
from src.domain.enums import MediaRequestStatus, ReleaseStatus


@dataclass(slots=True)
class ArrCompletion:
    """What Sonarr/Radarr reports about a request, independent of torrent state."""

    is_complete: bool
    # An arr only ever counts episodes that have aired, so a season that is still
    # running reads as complete every week between airings.
    has_unaired: bool = False


@dataclass(slots=True)
class DerivedRequestState:
    """Recomputed values for a single request."""

    status: MediaRequestStatus | _Unset
    newest_release_published_at: datetime | None


def season_completion(season: SeriesSeasonDetails) -> ArrCompletion:
    """The verdict a Sonarr season's own counts imply, shared by export and sync."""

    return ArrCompletion(
        is_complete=bool(season.episode_count)
        and season.episode_file_count >= season.episode_count,
        has_unaired=season.episode_count < season.total_episode_count,
    )


class RequestStateDeriver:
    """Pure rules for the state implied by a request's releases and arr verdict."""

    def derive(
        self,
        record: MediaRequestRecord,
        releases: Sequence[ReleaseRecord],
        arr: ArrCompletion | None = None,
    ) -> DerivedRequestState:
        return DerivedRequestState(
            status=self._derive_status(record, releases, arr),
            newest_release_published_at=self._newest_published_at(releases),
        )

    def _derive_status(
        self,
        record: MediaRequestRecord,
        releases: Sequence[ReleaseRecord],
        arr: ArrCompletion | None,
    ) -> MediaRequestStatus | _Unset:
        """Status implied by an arr verdict, else by the request's releases.

        Sonarr/Radarr are the only authority on `COMPLETED`: a torrent finishing
        or continuing to seed must never move a request into or out of it. With
        no verdict at all, a currently completed request is left untouched.

        `has_unaired` is part of that verdict and not a rule of its own: both arrs
        call a season complete once every episode that has aired holds a file,
        which is true of any season still running. Completing on that alone would
        close a request that has an episode yet to come, so a verdict carrying
        unaired episodes falls through to the release rules below -- monitoring
        for a release an indexer could improve on, pending otherwise.
        """
        if arr is not None:
            if arr.is_complete and not arr.has_unaired:
                return MediaRequestStatus.COMPLETED
            if record.status is MediaRequestStatus.COMPLETED:
                return MediaRequestStatus.PENDING
        elif record.status is MediaRequestStatus.COMPLETED:
            return UNSET

        in_flight = [
            release for release in releases if release.last_exported_info_hash != release.info_hash
        ]
        if in_flight:
            # A completed release stays in flight until the arr imports it, which
            # is IMPORTING rather than DOWNLOADING; a sibling that is still
            # transferring dominates, since the season is not yet all here.
            if any(release.status is ReleaseStatus.DOWNLOADING for release in in_flight):
                return MediaRequestStatus.DOWNLOADING
            if any(release.status is ReleaseStatus.COMPLETED for release in in_flight):
                return MediaRequestStatus.IMPORTING
            if all(release.status is ReleaseStatus.FAILED for release in in_flight):
                return MediaRequestStatus.FAILED
            return UNSET
        if any(self._is_regrabbable(release) for release in releases):
            return MediaRequestStatus.MONITORING
        # Nothing in flight and nothing left to regrab against: a release-driven
        # request with no more work settles on pending rather than being left
        # wherever it was, which is what heals a request whose last release
        # was deleted.
        return MediaRequestStatus.PENDING

    @staticmethod
    def _is_regrabbable(release: ReleaseRecord) -> bool:
        """Whether the re-grab pass could still find a better copy of this release."""
        return release.torrent_source is not None and release.torrent_source != MANUAL_SOURCE

    @staticmethod
    def _newest_published_at(releases: Sequence[ReleaseRecord]) -> datetime | None:
        published = [
            release.published_at for release in releases if release.published_at is not None
        ]
        return max(published, default=None)


__all__ = ["ArrCompletion", "DerivedRequestState", "RequestStateDeriver", "season_completion"]
