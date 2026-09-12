"""Utility to autocomplete release file mappings based on file names."""

from __future__ import annotations

import os
from collections.abc import Sequence
from dataclasses import dataclass, replace

from src.application.interfaces.releases import (
    FileMappingUpdateData,
    ReleaseFileMapping,
    ReleaseFileRecord,
    ReleaseRequestSnapshot,
)
from src.application.utility.release_parsing import (
    is_video_file,
    natural_sort_key,
    parse_episode,
)
from src.domain.enums import MediaType


@dataclass(slots=True)
class _Context:
    """Episode numbering carried over from the previous file in a folder."""

    seasons: dict[str, int]
    episodes: dict[tuple[str, int], int]


class ReleaseFileMatcher:
    """Infer request, season and episode for the files of a release.

    A release often spans several seasons (a complete-series pack) while each
    season is tracked by its own media request. Files are therefore matched to the
    request owning the season parsed out of the file, not to whichever request
    happened to grab the release.

    Season and episode numbers already stored on a file are left alone, since they
    may have been corrected by hand; only gaps are filled. The request a file points
    at is always re-derived from its season, which is what repairs a pack that was
    mapped entirely onto the grabbing request.
    """

    def autocomplete(
        self,
        files: list[ReleaseFileRecord],
        requests: Sequence[ReleaseRequestSnapshot] | None = None,
    ) -> list[FileMappingUpdateData]:
        """Return mapping updates for every file that can be resolved automatically."""

        by_season = self._index_by_season(requests or ())
        sole_season = next(iter(by_season)) if len(by_season) == 1 else None
        context = _Context(seasons={}, episodes={})
        updates: list[FileMappingUpdateData] = []

        for file in sorted(files, key=lambda item: natural_sort_key(item.path or item.name)):
            if not is_video_file(file.name):
                continue

            resolved = self._resolve(file, by_season, sole_season, context)
            if resolved is None or resolved == file.mapping:
                continue

            file.mapping = resolved
            updates.append(FileMappingUpdateData(file_id=file.id, mapping=resolved))

        return updates

    def seasons_in(self, files: Sequence[ReleaseFileRecord]) -> set[int]:
        """Return the season numbers detectable from a release's video files."""

        seasons: set[int] = set()
        for file in files:
            if not is_video_file(file.name):
                continue
            season = parse_episode(file.name, file.path).season
            if season is not None:
                seasons.add(season)
        return seasons

    def _resolve(
        self,
        file: ReleaseFileRecord,
        by_season: dict[int, ReleaseRequestSnapshot],
        sole_season: int | None,
        context: _Context,
    ) -> ReleaseFileMapping | None:
        directory = os.path.dirname(file.path or file.name)
        mapping = file.mapping
        parsed = parse_episode(file.name, file.path)

        season = self._first_of(
            mapping.season if mapping else None,
            parsed.season,
            context.seasons.get(directory),
            sole_season,
        )
        if season is None:
            return None

        previous = context.episodes.get((directory, season))
        episode = self._first_of(
            mapping.episode if mapping else None,
            parsed.episode,
            previous + 1 if previous is not None else None,
        )
        if episode is None:
            return None

        context.seasons[directory] = season
        context.episodes[(directory, season)] = episode

        request = by_season.get(season)
        if request is None:
            if mapping is None or mapping.request_id is None:
                return None
            return replace(mapping, mapping_type=MediaType.SERIES, season=season, episode=episode)

        return ReleaseFileMapping(
            mapping_type=MediaType.SERIES,
            request_id=request.id,
            request_title=request.title,
            season=season,
            episode=episode,
        )

    def _index_by_season(
        self,
        requests: Sequence[ReleaseRequestSnapshot],
    ) -> dict[int, ReleaseRequestSnapshot]:
        indexed: dict[int, ReleaseRequestSnapshot] = {}
        for request in requests:
            if request.media_type is MediaType.MOVIE or request.season_number is None:
                continue
            indexed.setdefault(request.season_number, request)
        return indexed

    def _first_of(self, *values: int | None) -> int | None:
        return next((value for value in values if value is not None), None)


__all__ = ["ReleaseFileMatcher"]
