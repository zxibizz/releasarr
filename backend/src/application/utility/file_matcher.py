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
    movie_titles,
    natural_sort_key,
    normalize_title,
    parse_episode,
    parse_year,
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
    happened to grab the release. Movies work the same way for a collection pack,
    matched on title instead of season.

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

        candidates = tuple(requests or ())
        by_season = self._index_by_season(candidates)
        sole_season = next(iter(by_season)) if len(by_season) == 1 else None
        movies = [request for request in candidates if request.media_type is MediaType.MOVIE]
        context = _Context(seasons={}, episodes={})
        updates: list[FileMappingUpdateData] = []
        unresolved: list[ReleaseFileRecord] = []

        for file in sorted(files, key=lambda item: natural_sort_key(item.path or item.name)):
            if not is_video_file(file.name):
                continue

            if self._is_movie_file(file):
                unresolved.append(file)
                continue

            resolved = self._resolve(file, by_season, sole_season, context)
            if resolved is None:
                if not self._is_episode_file(file):
                    unresolved.append(file)
                continue
            if resolved == file.mapping:
                continue

            file.mapping = resolved
            updates.append(FileMappingUpdateData(file_id=file.id, mapping=resolved))

        for file, resolved in self._resolve_movies(unresolved, movies):
            if resolved == file.mapping:
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

    def _is_movie_file(self, file: ReleaseFileRecord) -> bool:
        """Keep a file someone already declared a movie out of the series pass.

        Without this, a release that also carries series requests could pull the
        file onto a season purely because the release only spans one.
        """

        return file.mapping is not None and file.mapping.mapping_type is MediaType.MOVIE

    def _is_episode_file(self, file: ReleaseFileRecord) -> bool:
        """Report whether a file names an episode outright.

        Such a file belongs to a season even when no request covers it, so it
        must not fall through to the movie pass. A lone season number is not
        enough: it is just as likely to be part of a title ("Ocean's 8").
        """

        parsed = parse_episode(file.name, file.path)
        return parsed.season is not None and parsed.episode is not None

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

    def _resolve_movies(
        self,
        files: Sequence[ReleaseFileRecord],
        movies: Sequence[ReleaseRequestSnapshot],
    ) -> list[tuple[ReleaseFileRecord, ReleaseFileMapping]]:
        """Match the files no season could be read out of onto movie requests."""

        if not files or not movies:
            return []

        if len(movies) == 1:
            if self._already_mapped_to(files, movies[0]):
                return []
            # A single-movie release is the feature plus extras, samples and
            # trailers. Only the largest file is the movie, and importing one of
            # the others into Radarr would replace the real thing.
            largest = max(files, key=lambda file: file.size_bytes)
            return [(largest, self._movie_mapping(movies[0]))]

        titles = self._index_by_title(movies)
        matched: list[tuple[ReleaseFileRecord, ReleaseFileMapping]] = []
        for file in files:
            request = self._match_by_title(file, titles)
            if request is not None:
                matched.append((file, self._movie_mapping(request)))
        return matched

    def _already_mapped_to(
        self,
        files: Sequence[ReleaseFileRecord],
        request: ReleaseRequestSnapshot,
    ) -> bool:
        """Whether the movie already has its file picked out.

        Picking the largest file is a guess, and someone who corrected it must
        not have the guess put straight back on the next run.
        """

        return any(
            file.mapping is not None and file.mapping.request_id == request.id for file in files
        )

    def _index_by_title(
        self,
        movies: Sequence[ReleaseRequestSnapshot],
    ) -> dict[str, list[ReleaseRequestSnapshot]]:
        indexed: dict[str, list[ReleaseRequestSnapshot]] = {}
        for movie in movies:
            for title in (movie.title, *movie.alternate_titles):
                key = normalize_title(title or "")
                if key and movie not in indexed.setdefault(key, []):
                    indexed[key].append(movie)
        return indexed

    def _match_by_title(
        self,
        file: ReleaseFileRecord,
        titles: dict[str, list[ReleaseRequestSnapshot]],
    ) -> ReleaseRequestSnapshot | None:
        """Find the one request a file's name spells out.

        The title has to match in full rather than merely appear in the name,
        or ``Iron Man 2`` would claim ``Iron.Man.2008`` as its own.
        """

        for candidate in movie_titles(file.name, file.path):
            matches = titles.get(candidate)
            if not matches:
                continue
            if len(matches) == 1:
                return matches[0]
            # A remake shares its title with the original, so only the year
            # separates them. Without one, mapping is left to a person.
            year = parse_year(file.name, file.path)
            return next((movie for movie in matches if movie.year == year), None)
        return None

    def _movie_mapping(self, request: ReleaseRequestSnapshot) -> ReleaseFileMapping:
        return ReleaseFileMapping(
            mapping_type=MediaType.MOVIE,
            request_id=request.id,
            request_title=request.title,
            season=None,
            episode=None,
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
