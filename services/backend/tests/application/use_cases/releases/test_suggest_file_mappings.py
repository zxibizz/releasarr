"""Unit tests for the non-persisting file mapping suggestions."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from src.application.interfaces.releases import (
    FileMappingUpdateData,
    ReleaseFileMapping,
    ReleaseFileRecord,
    ReleaseRecord,
    ReleaseRequestSnapshot,
)
from src.application.use_cases.releases.auto_mapping import ReleaseAutoMapper
from src.application.use_cases.releases.exceptions import ReleaseNotFoundError
from src.application.use_cases.releases.suggest_file_mappings import (
    SuggestReleaseFileMappingsUseCase,
)
from src.application.utility.file_matcher import ReleaseFileMatcher
from src.domain.enums import MediaType, ReleaseStatus


def make_file(file_id: str, path: str) -> ReleaseFileRecord:
    return ReleaseFileRecord(
        id=file_id,
        name=path.rsplit("/", 1)[-1],
        size_bytes=2048,
        path=path,
        mapping=None,
    )


def make_request(request_id: str, season: int) -> ReleaseRequestSnapshot:
    return ReleaseRequestSnapshot(
        id=request_id,
        sonarr_series_id=42,
        title=f"Avatar - Season {season}",
        media_type=MediaType.SERIES,
        season_number=season,
    )


def make_release(
    files: list[ReleaseFileRecord],
    requests: list[ReleaseRequestSnapshot],
) -> ReleaseRecord:
    return ReleaseRecord(
        id="rel-1",
        name="Avatar Complete",
        info_hash="hash-rel-1",
        size_bytes=1024,
        status=ReleaseStatus.COMPLETED,
        progress=100.0,
        download_speed=0.0,
        upload_speed=0.0,
        seeders=1,
        leechers=0,
        ratio=1.0,
        added_at=datetime.now(UTC),
        completed_at=None,
        request_ids=[request.id for request in requests],
        torrent_source="indexer",
        quality="1080p",
        requests=requests,
        last_exported_info_hash=None,
        export_failures_count=0,
        files=files,
    )


class FakeReleaseRepository:
    def __init__(self, release: ReleaseRecord | None) -> None:
        self.release = release
        self.writes: list[list[FileMappingUpdateData]] = []

    async def get_release(self, release_id: str) -> ReleaseRecord | None:
        if self.release is None or self.release.id != release_id:
            return None
        return self.release

    async def update_file_mappings(
        self,
        release_id: str,
        updates: list[FileMappingUpdateData],
    ) -> bool:
        self.writes.append(updates)
        return True


def build_use_case(
    repository: FakeReleaseRepository,
) -> SuggestReleaseFileMappingsUseCase:
    auto_mapper = ReleaseAutoMapper(
        repository=repository,  # type: ignore[arg-type]
        file_matcher=ReleaseFileMatcher(),
    )
    return SuggestReleaseFileMappingsUseCase(
        repository=repository,  # type: ignore[arg-type]
        auto_mapper=auto_mapper,
    )


async def test_suggestions_cover_every_file_the_matcher_resolves() -> None:
    release = make_release(
        files=[
            make_file("a", "Avatar/Avatar.S01E01.mkv"),
            make_file("b", "Avatar/Avatar.S02E03.mkv"),
        ],
        requests=[make_request("req-1", 1), make_request("req-2", 2)],
    )
    repository = FakeReleaseRepository(release)

    suggestions = await build_use_case(repository).execute("rel-1")

    assert [(item.file_id, item.request_mapping.request_id) for item in suggestions] == [
        ("a", "req-1"),
        ("b", "req-2"),
    ]
    assert suggestions[1].request_mapping.season == 2
    assert suggestions[1].request_mapping.episode == 3
    assert suggestions[1].request_mapping.mapping_type == MediaType.SERIES.value


async def test_suggesting_stores_nothing() -> None:
    """The user decides: a proposal the form never saves must leave no trace."""

    release = make_release(
        files=[make_file("a", "Avatar/Avatar.S01E01.mkv")],
        requests=[make_request("req-1", 1)],
    )
    repository = FakeReleaseRepository(release)

    await build_use_case(repository).execute("rel-1")

    assert repository.writes == []


async def test_files_the_matcher_cannot_place_are_left_out() -> None:
    """Extras sit outside the season folders, and no request claims them."""

    release = make_release(
        files=[
            make_file("a", "Avatar/Season 1/Avatar.S01E01.mkv"),
            make_file("b", "Avatar/Extras/behind the scenes.mkv"),
            make_file("c", "Avatar/Season 1/Avatar.S01E01.nfo"),
        ],
        requests=[make_request("req-1", 1), make_request("req-2", 2)],
    )
    repository = FakeReleaseRepository(release)

    suggestions = await build_use_case(repository).execute("rel-1")

    assert [item.file_id for item in suggestions] == ["a"]


async def test_a_mapping_already_stored_is_not_offered_again() -> None:
    file_record = make_file("a", "Avatar/Avatar.S01E01.mkv")
    file_record.mapping = ReleaseFileMapping(
        mapping_type=MediaType.SERIES,
        request_id="req-1",
        request_title="Avatar - Season 1",
        season=1,
        episode=1,
    )
    repository = FakeReleaseRepository(
        make_release(files=[file_record], requests=[make_request("req-1", 1)])
    )

    assert await build_use_case(repository).execute("rel-1") == []


async def test_an_unknown_release_is_rejected() -> None:
    repository = FakeReleaseRepository(None)

    with pytest.raises(ReleaseNotFoundError):
        await build_use_case(repository).execute("missing")
