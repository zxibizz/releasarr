"""Detect conditions worth surfacing on a release but not worth blocking on."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from src.application.interfaces.releases import (
    ReleaseFileMapping,
    ReleaseRecord,
    ReleaseRequestSnapshot,
    ReleaseWarning,
)
from src.domain.enums import MediaType, ReleaseWarningCode

TargetKey = tuple[object, ...]


class ReleaseWarningEvaluator:
    """Flag files across a set of releases that resolve to the same arr target.

    Two releases linked to the same request can each carry a file mapped to the
    same episode or movie - a second grab of an already-covered season, or a
    pack with two files for one episode inside a single release. Keying on the
    resolved Sonarr/Radarr target rather than the request id is what also
    catches two different requests that happen to track the same series: the
    export path resolves against `sonarr_series_id`/`radarr_movie_id`, not the
    request, and nothing binds `file.season` to `request.season_number`.
    """

    def evaluate(self, releases: Sequence[ReleaseRecord]) -> dict[str, list[ReleaseWarning]]:
        """Return the warnings for each release id that has any, keyed by id."""

        buckets: dict[TargetKey, list[tuple[str, str]]] = defaultdict(list)

        for release in releases:
            snapshots = {snapshot.id: snapshot for snapshot in release.requests}
            for file in release.files:
                mapping = file.mapping
                if mapping is None or not mapping.request_id:
                    continue
                key = self._target_key(mapping, snapshots.get(mapping.request_id))
                if key is None:
                    continue
                buckets[key].append((release.id, file.id))

        file_ids_by_release: dict[str, set[str]] = defaultdict(set)
        related_by_release: dict[str, set[str]] = defaultdict(set)

        for entries in buckets.values():
            if len(entries) < 2:
                continue
            release_ids = {release_id for release_id, _ in entries}
            for release_id, file_id in entries:
                file_ids_by_release[release_id].add(file_id)
                related_by_release[release_id].update(release_ids - {release_id})

        return {
            release_id: [
                ReleaseWarning(
                    code=ReleaseWarningCode.MAPPING_OVERLAP,
                    file_ids=sorted(file_ids),
                    related_release_ids=sorted(related_by_release[release_id]),
                )
            ]
            for release_id, file_ids in file_ids_by_release.items()
        }

    @staticmethod
    def _target_key(
        mapping: ReleaseFileMapping,
        snapshot: ReleaseRequestSnapshot | None,
    ) -> TargetKey | None:
        if mapping.mapping_type is MediaType.MOVIE:
            movie_id = snapshot.radarr_movie_id if snapshot else None
            target = movie_id if movie_id is not None else f"request:{mapping.request_id}"
            return ("movie", target)

        if mapping.mapping_type is MediaType.SERIES:
            if mapping.season is None or mapping.episode is None:
                return None
            series_id = snapshot.sonarr_series_id if snapshot else None
            target = series_id if series_id is not None else f"request:{mapping.request_id}"
            return ("series", target, mapping.season, mapping.episode)

        return None


__all__ = ["ReleaseWarningEvaluator"]
