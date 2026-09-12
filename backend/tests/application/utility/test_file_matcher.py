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


def make_movie_request(
    request_id: str,
    title: str,
    *,
    year: int | None = None,
    alternate_titles: list[str] | None = None,
) -> ReleaseRequestSnapshot:
    return ReleaseRequestSnapshot(
        id=request_id,
        sonarr_series_id=None,
        title=title,
        media_type=MediaType.MOVIE,
        season_number=None,
        radarr_movie_id=hash(request_id) % 1000,
        year=year,
        alternate_titles=alternate_titles or [],
    )


def sized_file(file_id: str, path: str, size_bytes: int) -> ReleaseFileRecord:
    file = make_file(file_id, path)
    file.size_bytes = size_bytes
    return file


def test_the_feature_of_a_single_movie_release_is_its_largest_file() -> None:
    """Importing a sample or a featurette would replace the movie in Radarr."""

    files = [
        sized_file("sample", "Arrival.2016.1080p/Sample/sample.mkv", 30_000_000),
        sized_file("feature", "Arrival.2016.1080p/arrival.2016.1080p.mkv", 8_000_000_000),
        sized_file("extra", "Arrival.2016.1080p/Extras/behind-the-scenes.mkv", 400_000_000),
    ]

    ReleaseFileMatcher().autocomplete(files, [make_movie_request("req-movie", "Arrival")])

    assert [file.id for file in files if file.mapping is not None] == ["feature"]
    assert mapping_of(files[1]).mapping_type is MediaType.MOVIE
    assert mapping_of(files[1]).request_id == "req-movie"


def test_a_hand_picked_movie_file_survives_the_next_run() -> None:
    """Picking the largest file is a guess, so a correction has to outrank it."""

    request = make_movie_request("req-movie", "Arrival")
    files = [
        sized_file("chosen", "Arrival.2016/part-one.mkv", 4_000_000_000),
        sized_file("largest", "Arrival.2016/part-two.mkv", 5_000_000_000),
    ]
    files[0].mapping = ReleaseFileMapping(
        mapping_type=MediaType.MOVIE,
        request_id="req-movie",
        request_title="Arrival",
        season=None,
        episode=None,
    )

    assert ReleaseFileMatcher().autocomplete(files, [request]) == []
    assert files[1].mapping is None


def test_a_collection_pack_is_split_across_its_movies_by_title() -> None:
    files = [
        sized_file("a", "Nolan/The.Dark.Knight.2008.1080p.mkv", 8_000_000_000),
        sized_file("b", "Nolan/Inception.2010.1080p.mkv", 9_000_000_000),
    ]
    requests = [
        make_movie_request("req-tdk", "The Dark Knight", year=2008),
        make_movie_request("req-inception", "Inception", year=2010),
    ]

    ReleaseFileMatcher().autocomplete(files, requests)

    assert [mapping_of(file).request_id for file in files] == ["req-tdk", "req-inception"]


def test_a_sequel_wins_over_the_title_contained_in_its_name() -> None:
    files = [
        sized_file("a", "Marvel/Iron.Man.2008.1080p.mkv", 8_000_000_000),
        sized_file("b", "Marvel/Iron.Man.2.2010.1080p.mkv", 8_000_000_000),
    ]
    requests = [
        make_movie_request("req-im1", "Iron Man", year=2008),
        make_movie_request("req-im2", "Iron Man 2", year=2010),
    ]

    ReleaseFileMatcher().autocomplete(files, requests)

    assert [mapping_of(file).request_id for file in files] == ["req-im1", "req-im2"]


def test_a_release_named_in_another_language_matches_a_localized_request() -> None:
    """A movie's own title is whichever language won, so the others must match too."""

    files = [
        sized_file("a", "Кино/Прибытие.2016.1080p.mkv", 8_000_000_000),
        sized_file("b", "Кино/Дюна.2021.1080p.mkv", 9_000_000_000),
    ]
    requests = [
        make_movie_request("req-arrival", "Arrival", alternate_titles=["Прибытие"]),
        make_movie_request("req-dune", "Dune", alternate_titles=["Дюна"]),
    ]

    ReleaseFileMatcher().autocomplete(files, requests)

    assert [mapping_of(file).request_id for file in files] == ["req-arrival", "req-dune"]


def test_an_unmatched_file_in_a_collection_pack_is_left_for_manual_mapping() -> None:
    files = [
        sized_file("a", "Nolan/Inception.2010.1080p.mkv", 9_000_000_000),
        sized_file("b", "Nolan/Tenet.2020.1080p.mkv", 9_000_000_000),
    ]
    requests = [
        make_movie_request("req-inception", "Inception", year=2010),
        make_movie_request("req-tdk", "The Dark Knight", year=2008),
    ]

    ReleaseFileMatcher().autocomplete(files, requests)

    assert mapping_of(files[0]).request_id == "req-inception"
    assert files[1].mapping is None


def test_a_movie_whose_title_reads_as_a_season_still_matches() -> None:
    """``Ocean's 8`` parses as season 8, which must not make it an episode."""

    files = [sized_file("a", "Oceans.8.2018.1080p.BluRay.x264.mkv", 8_000_000_000)]

    ReleaseFileMatcher().autocomplete(files, [make_movie_request("req-movie", "Ocean's 8")])

    assert mapping_of(files[0]).request_id == "req-movie"
    assert mapping_of(files[0]).mapping_type is MediaType.MOVIE


def test_seasons_in_reports_only_video_files() -> None:
    files = [
        make_file("a", "Avatar/Avatar.S01E01.mkv"),
        make_file("b", "Avatar/Avatar.S02E01.mkv"),
        make_file("c", "Avatar/Avatar.S09E01.nfo"),
    ]

    assert ReleaseFileMatcher().seasons_in(files) == {1, 2}
