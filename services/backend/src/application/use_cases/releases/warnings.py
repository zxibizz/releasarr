"""Detect conditions worth surfacing on a release but not worth blocking on."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from src.application.interfaces.releases import (
    ReleaseFileMapping,
    ReleaseRecord,
    ReleaseRepository,
    ReleaseRequestSnapshot,
    ReleaseWarning,
)
from src.application.interfaces.request_warnings import (
    RequestWarningRecord,
    RequestWarningRepository,
)
from src.domain.enums import MediaType, RequestWarningCode

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
                    code=RequestWarningCode.MAPPING_OVERLAP,
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


class RequestWarningSynchronizer:
    """Persist `ReleaseWarningEvaluator`'s output as `request_warnings` rows.

    The one place that knows how to turn a release-keyed detector result into
    rows scoped by request - every call site that can change a mapping goes
    through `sync_for_requests` rather than writing rows itself.
    """

    def __init__(
        self,
        repository: ReleaseRepository,
        warning_repository: RequestWarningRepository,
        evaluator: ReleaseWarningEvaluator | None = None,
    ) -> None:
        self._repository = repository
        self._warning_repository = warning_repository
        self._evaluator = evaluator or ReleaseWarningEvaluator()

    async def sync_for_requests(self, request_ids: Sequence[str]) -> None:
        """Recompute `MAPPING_OVERLAP` for every one of `request_ids`.

        Loads every release linked to any of them - the evaluator buckets
        across a request's *whole* release set, so a partial load would
        under-detect an overlap spanning a release left out - then replaces
        that code's rows for exactly `request_ids`, which is what clears a
        release that stopped overlapping.
        """

        ids = sorted({request_id for request_id in request_ids if request_id})
        if not ids:
            return

        id_set = set(ids)
        releases = await self._repository.get_releases_for_requests(ids)
        warnings_by_release = self._evaluator.evaluate(releases)

        rows = [
            RequestWarningRecord(
                request_id=request_id,
                release_id=release.id,
                code=RequestWarningCode.MAPPING_OVERLAP,
                details={
                    "file_ids": warning.file_ids,
                    "related_release_ids": warning.related_release_ids,
                },
            )
            for release in releases
            for warning in warnings_by_release.get(release.id, [])
            # A release can be shared with a request outside our recompute
            # scope; that request's own rows are left for its own sync to touch.
            for request_id in release.request_ids
            if request_id in id_set
        ]
        await self._warning_repository.replace_for_requests(
            RequestWarningCode.MAPPING_OVERLAP, ids, rows
        )


def rows_to_release_warnings(rows: Sequence[RequestWarningRecord]) -> list[ReleaseWarning]:
    """Reconstruct a release's own warning view from persisted rows.

    Only `MAPPING_OVERLAP` carries the file-level detail a release's own view
    needs; other codes (e.g. a regrab failure) are request-level concerns and
    stay off this list. One row exists per request sharing the release, all
    carrying identical detail for the same code, so the first one seen is
    enough.
    """

    seen: set[RequestWarningCode] = set()
    warnings: list[ReleaseWarning] = []
    for row in rows:
        if row.code is not RequestWarningCode.MAPPING_OVERLAP or row.code in seen:
            continue
        seen.add(row.code)
        details = row.details or {}
        warnings.append(
            ReleaseWarning(
                code=row.code,
                file_ids=_as_str_list(details.get("file_ids")),
                related_release_ids=_as_str_list(details.get("related_release_ids")),
                details=row.details,
            )
        )
    return warnings


def _as_str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


__all__ = ["ReleaseWarningEvaluator", "RequestWarningSynchronizer", "rows_to_release_warnings"]
