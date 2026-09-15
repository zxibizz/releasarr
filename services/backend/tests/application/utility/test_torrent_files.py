"""Tests for matching a release's stored files against a replacement's file list."""

from __future__ import annotations

from src.application.interfaces.releases import ReleaseFileMapping, ReleaseFileRecord
from src.application.utility.torrent_files import reconcile_release_files
from src.domain.enums import MediaType

ROOT = "Show.S01.1080p.WEB-DL"
REPACK = "Show.S01.1080p.REPACK-GRP"


def file(file_id: str, path: str) -> ReleaseFileRecord:
    return ReleaseFileRecord(id=file_id, name=path, size_bytes=1024, path=path, mapping=None)


def episode(file_id: str, path: str, number: int) -> ReleaseFileRecord:
    return ReleaseFileRecord(
        id=file_id,
        name=path,
        size_bytes=4096,
        path=path,
        mapping=ReleaseFileMapping(
            mapping_type=MediaType.SERIES,
            request_id="req-1",
            request_title="Show",
            season=1,
            episode=number,
        ),
    )


def test_identical_file_lists_match_every_file_and_add_nothing() -> None:
    stored = [episode("file-1", f"{ROOT}/Show.S01E01.mkv", 1)]
    incoming = [file("new-1", f"{ROOT}/Show.S01E01.mkv")]

    result = reconcile_release_files(stored, incoming)

    assert result.missing == []
    assert result.added == []
    assert result.matched == [("file-1", incoming[0])]


def test_a_renamed_root_folder_still_matches_by_name() -> None:
    """A repack that renamed only the torrent's root is the same files."""

    stored = [episode("file-1", f"{ROOT}/Show.S01E01.mkv", 1)]
    incoming = [file("new-1", f"{REPACK}/Show.S01E01.mkv")]

    result = reconcile_release_files(stored, incoming)

    assert result.missing == []
    assert result.added == []
    assert [existing_id for existing_id, _ in result.matched] == ["file-1"]


def test_files_the_torrent_does_not_carry_are_reported_missing() -> None:
    stored = [
        episode("file-1", f"{ROOT}/Show.S01E01.mkv", 1),
        episode("file-2", f"{ROOT}/Show.S01E02.mkv", 2),
    ]
    incoming = [file("new-1", f"{ROOT}/Show.S01E01.mkv")]

    result = reconcile_release_files(stored, incoming)

    assert [record.id for record in result.missing] == ["file-2"]
    assert [existing_id for existing_id, _ in result.matched] == ["file-1"]
    assert result.added == []


def test_files_the_release_did_not_have_are_added() -> None:
    stored = [episode("file-1", f"{ROOT}/Show.S01E01.mkv", 1)]
    incoming = [
        file("new-1", f"{ROOT}/Show.S01E01.mkv"),
        file("new-2", f"{ROOT}/Show.S01E02.mkv"),
    ]

    result = reconcile_release_files(stored, incoming)

    assert result.missing == []
    assert [record.id for record in result.added] == ["new-2"]


def test_colliding_names_are_not_paired_when_the_counts_differ() -> None:
    """Two `01.mkv` and one incoming file is not enough to guess which is which."""

    stored = [
        episode("file-1", "Old/Season 1/01.mkv", 1),
        episode("file-2", "Old/Season 2/01.mkv", 2),
    ]
    incoming = [file("new-1", "New/Season 1/01.mkv")]

    result = reconcile_release_files(stored, incoming)

    assert [record.id for record in result.missing] == ["file-1", "file-2"]
    assert result.matched == []
    assert [record.id for record in result.added] == ["new-1"]


def test_colliding_names_are_paired_in_order_when_the_counts_agree() -> None:
    stored = [
        episode("file-1", "Old/Season 1/01.mkv", 1),
        episode("file-2", "Old/Season 2/01.mkv", 2),
    ]
    incoming = [
        file("new-2", "New/Season 2/01.mkv"),
        file("new-1", "New/Season 1/01.mkv"),
    ]

    result = reconcile_release_files(stored, incoming)

    assert result.missing == []
    assert result.added == []
    assert [(existing_id, record.id) for existing_id, record in result.matched] == [
        ("file-1", "new-1"),
        ("file-2", "new-2"),
    ]


def test_paths_are_compared_without_case_or_platform_separators() -> None:
    stored = [episode("file-1", f"{ROOT}/Show.S01E01.mkv", 1)]
    incoming = [file("new-1", f"{ROOT}\\show.s01e01.MKV")]

    result = reconcile_release_files(stored, incoming)

    assert result.missing == []
    assert [existing_id for existing_id, _ in result.matched] == ["file-1"]


def test_a_release_with_no_stored_files_takes_the_whole_list() -> None:
    """A magnet-only grab has no rows, so everything the torrent lists is new."""

    incoming = [
        file("new-1", f"{ROOT}/Show.S01E01.mkv"),
        file("new-2", f"{ROOT}/Show.S01E02.mkv"),
    ]

    result = reconcile_release_files([], incoming)

    assert result.matched == []
    assert result.missing == []
    assert result.added == incoming
