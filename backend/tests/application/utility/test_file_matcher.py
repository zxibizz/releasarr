"""Tests for automatic release file mapping."""

from __future__ import annotations

from src.application.interfaces.releases import (
    ReleaseFileMapping,
    ReleaseFileRecord,
    ReleaseRequestSnapshot,
)
from src.application.utility.file_matcher import ReleaseFileMatcher
from src.domain.enums import MediaType


def make_file(
    file_id: str,
    path: str,
    *,
    mapping: ReleaseFileMapping | None = None,
) -> ReleaseFileRecord:
    return ReleaseFileRecord(
        id=file_id,
        name=path.rsplit("/", 1)[-1],
        size_bytes=2048,
        path=path,
        mapping=mapping,
    )


def make_request(request_id: str, season: int) -> ReleaseRequestSnapshot:
    return ReleaseRequestSnapshot(
        id=request_id,
        sonarr_series_id=42,
        title=f"Avatar - Season {season}",
        media_type=MediaType.SERIES,
        season_number=season,
    )


def mapping_of(file: ReleaseFileRecord) -> ReleaseFileMapping:
    assert file.mapping is not None, f"{file.name} was left unmapped"
    return file.mapping


def placements(files: list[ReleaseFileRecord]) -> list[tuple[str | None, int | None, int | None]]:
    return [
        (mapping.request_id, mapping.season, mapping.episode)
        for mapping in (mapping_of(file) for file in files)
    ]


def test_files_are_mapped_to_the_request_owning_their_season() -> None:
    files = [
        make_file("a", "Avatar/Avatar.S01E01.mkv"),
        make_file("b", "Avatar/Avatar.S02E01.mkv"),
        make_file("c", "Avatar/Avatar.S03E21.mkv"),
    ]
    requests = [make_request("req-1", 1), make_request("req-2", 2), make_request("req-3", 3)]

    ReleaseFileMatcher().autocomplete(files, requests)

    assert placements(files) == [("req-1", 1, 1), ("req-2", 2, 1), ("req-3", 3, 21)]


def test_season_folders_route_files_without_episode_markers() -> None:
    files = [
        make_file("a", "Avatar/Season 1/01 - The Boy in the Iceberg.mkv"),
        make_file("b", "Avatar/Season 2/01 - The Avatar State.mkv"),
    ]
    requests = [make_request("req-1", 1), make_request("req-2", 2)]

    ReleaseFileMatcher().autocomplete(files, requests)

    assert placements(files) == [("req-1", 1, 1), ("req-2", 2, 1)]


def test_a_pack_mapped_onto_a_single_request_is_repaired() -> None:
    """The grabbing season's request is corrected to the season each file belongs to."""

    wrong = ReleaseFileMapping(
        mapping_type=MediaType.SERIES,
        request_id="req-1",
        request_title="Avatar - Season 1",
        season=2,
        episode=4,
    )
    files = [make_file("a", "Avatar/Avatar.S02E04.mkv", mapping=wrong)]
    requests = [make_request("req-1", 1), make_request("req-2", 2)]

    updates = ReleaseFileMatcher().autocomplete(files, requests)

    assert len(updates) == 1
    assert placements(files) == [("req-2", 2, 4)]


def test_existing_season_and_episode_numbers_are_preserved() -> None:
    """A hand-corrected mapping must survive a later automapping pass."""

    manual = ReleaseFileMapping(
        mapping_type=MediaType.SERIES,
        request_id="req-2",
        request_title="Avatar - Season 2",
        season=2,
        episode=9,
    )
    files = [make_file("a", "Avatar/Avatar.S02E04.mkv", mapping=manual)]

    updates = ReleaseFileMatcher().autocomplete(files, [make_request("req-2", 2)])

    assert updates == []
    assert files[0].mapping == manual


def test_episode_numbers_continue_sequentially_within_a_season_folder() -> None:
    files = [
        make_file("a", "Avatar/Season 2/Avatar.S02E01.mkv"),
        make_file("b", "Avatar/Season 2/Avatar.The.Chase.mkv"),
        make_file("c", "Avatar/Season 3/Avatar.S03E01.mkv"),
        make_file("d", "Avatar/Season 3/Avatar.The.Headband.mkv"),
    ]
    requests = [make_request("req-2", 2), make_request("req-3", 3)]

    ReleaseFileMatcher().autocomplete(files, requests)

    assert placements(files) == [
        ("req-2", 2, 1),
        ("req-2", 2, 2),
        ("req-3", 3, 1),
        ("req-3", 3, 2),
    ]


def test_sequencing_follows_natural_order_rather_than_lexicographic() -> None:
    """Lexicographic order would place ``E10`` before ``E9`` and mis-number the rest."""

    files = [
        make_file("a", "Avatar/Avatar.S01E9.mkv"),
        make_file("b", "Avatar/Avatar.S01E10.mkv"),
        make_file("c", "Avatar/Avatar.zz.Untitled.mkv"),
    ]

    ReleaseFileMatcher().autocomplete(files, [make_request("req-1", 1)])

    assert mapping_of(files[2]).episode == 11


def test_non_video_files_are_left_unmapped() -> None:
    files = [
        make_file("a", "Avatar/Avatar.S01E01.mkv"),
        make_file("b", "Avatar/Avatar.S01E01.nfo"),
    ]

    ReleaseFileMatcher().autocomplete(files, [make_request("req-1", 1)])

    assert files[1].mapping is None


def test_files_of_an_unrequested_season_are_skipped() -> None:
    files = [
        make_file("a", "Avatar/Avatar.S01E01.mkv"),
        make_file("b", "Avatar/Avatar.S04E01.mkv"),
    ]

    ReleaseFileMatcher().autocomplete(files, [make_request("req-1", 1)])

    assert files[0].mapping is not None
    assert files[1].mapping is None


def test_a_single_request_absorbs_files_with_no_detectable_season() -> None:
    files = [make_file("a", "Avatar/Avatar.The.Last.Airbender.E03.mkv")]

    ReleaseFileMatcher().autocomplete(files, [make_request("req-2", 2)])

    assert placements(files) == [("req-2", 2, 3)]


def test_movie_requests_are_never_used_for_series_files() -> None:
    movie = ReleaseRequestSnapshot(
        id="req-movie",
        sonarr_series_id=None,
        title="Avatar",
        media_type=MediaType.MOVIE,
        season_number=None,
    )
    files = [make_file("a", "Avatar/Avatar.S01E01.mkv")]

    assert ReleaseFileMatcher().autocomplete(files, [movie]) == []


def test_seasons_in_reports_only_video_files() -> None:
    files = [
        make_file("a", "Avatar/Avatar.S01E01.mkv"),
        make_file("b", "Avatar/Avatar.S02E01.mkv"),
        make_file("c", "Avatar/Avatar.S09E01.nfo"),
    ]

    assert ReleaseFileMatcher().seasons_in(files) == {1, 2}
