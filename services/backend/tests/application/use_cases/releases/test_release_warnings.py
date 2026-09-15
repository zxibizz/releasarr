"""Unit tests for ReleaseWarningEvaluator."""

from __future__ import annotations

from datetime import UTC, datetime

from src.application.interfaces.releases import (
    ReleaseFileMapping,
    ReleaseFileRecord,
    ReleaseRecord,
    ReleaseRequestSnapshot,
)
from src.application.interfaces.request_warnings import RequestWarningRecord
from src.application.use_cases.releases.warnings import (
    ReleaseWarningEvaluator,
    RequestWarningSynchronizer,
    rows_to_release_warnings,
)
from src.domain.enums import MediaType, ReleaseStatus, RequestWarningCode


def make_file(
    file_id: str,
    *,
    request_id: str | None = None,
    mapping_type: MediaType | None = None,
    season: int | None = None,
    episode: int | None = None,
) -> ReleaseFileRecord:
    mapping = None
    if mapping_type is not None:
        mapping = ReleaseFileMapping(
            mapping_type=mapping_type,
            request_id=request_id,
            request_title=None,
            season=season,
            episode=episode,
        )
    return ReleaseFileRecord(
        id=file_id, name=f"{file_id}.mkv", size_bytes=1024, path=f"{file_id}.mkv", mapping=mapping
    )


def make_release(
    release_id: str,
    files: list[ReleaseFileRecord],
    requests: list[ReleaseRequestSnapshot],
) -> ReleaseRecord:
    now = datetime.now(UTC)
    return ReleaseRecord(
        id=release_id,
        name=release_id,
        info_hash=f"hash-{release_id}",
        size_bytes=1024,
        status=ReleaseStatus.DOWNLOADING,
        progress=0.0,
        download_speed=0.0,
        upload_speed=0.0,
        seeders=0,
        leechers=0,
        ratio=0.0,
        added_at=now,
        completed_at=None,
        request_ids=[req.id for req in requests],
        requests=requests,
        torrent_source="indexer",
        quality="1080p",
        files=files,
        last_exported_info_hash=None,
        export_failures_count=0,
    )


def series_request(request_id: str, *, sonarr_series_id: int | None = 42) -> ReleaseRequestSnapshot:
    return ReleaseRequestSnapshot(
        id=request_id,
        sonarr_series_id=sonarr_series_id,
        title=f"Series {request_id}",
        media_type=MediaType.SERIES,
        season_number=1,
    )


def movie_request(request_id: str, *, radarr_movie_id: int | None = 7) -> ReleaseRequestSnapshot:
    return ReleaseRequestSnapshot(
        id=request_id,
        sonarr_series_id=None,
        title=f"Movie {request_id}",
        media_type=MediaType.MOVIE,
        radarr_movie_id=radarr_movie_id,
    )


def series_file(
    file_id: str, request_id: str, season: int = 1, episode: int = 1
) -> ReleaseFileRecord:
    return make_file(
        file_id,
        request_id=request_id,
        mapping_type=MediaType.SERIES,
        season=season,
        episode=episode,
    )


def test_no_releases_means_no_warnings() -> None:
    assert ReleaseWarningEvaluator().evaluate([]) == {}


def test_complementary_episodes_produce_no_warning() -> None:
    request = series_request("req-1")
    release = make_release(
        "rel-1",
        files=[
            make_file("f1", request_id="req-1", mapping_type=MediaType.SERIES, season=1, episode=1),
            make_file("f2", request_id="req-1", mapping_type=MediaType.SERIES, season=1, episode=2),
        ],
        requests=[request],
    )

    assert ReleaseWarningEvaluator().evaluate([release]) == {}


def test_two_files_in_one_release_mapped_to_same_episode_warn_without_related_release() -> None:
    request = series_request("req-1")
    release = make_release(
        "rel-1",
        files=[
            make_file("f1", request_id="req-1", mapping_type=MediaType.SERIES, season=1, episode=1),
            make_file("f2", request_id="req-1", mapping_type=MediaType.SERIES, season=1, episode=1),
        ],
        requests=[request],
    )

    warnings = ReleaseWarningEvaluator().evaluate([release])

    assert set(warnings["rel-1"][0].file_ids) == {"f1", "f2"}
    assert warnings["rel-1"][0].code is RequestWarningCode.MAPPING_OVERLAP
    assert warnings["rel-1"][0].related_release_ids == []


def test_two_releases_mapped_to_same_episode_of_same_request_warn_each_other() -> None:
    request = series_request("req-1")
    release_a = make_release("rel-a", files=[series_file("fa", "req-1")], requests=[request])
    release_b = make_release("rel-b", files=[series_file("fb", "req-1")], requests=[request])

    warnings = ReleaseWarningEvaluator().evaluate([release_a, release_b])

    assert warnings["rel-a"][0].file_ids == ["fa"]
    assert warnings["rel-a"][0].related_release_ids == ["rel-b"]
    assert warnings["rel-b"][0].file_ids == ["fb"]
    assert warnings["rel-b"][0].related_release_ids == ["rel-a"]


def test_two_requests_sharing_a_sonarr_series_id_still_collide() -> None:
    """Two different requests can track the same series; the export path resolves
    against sonarr_series_id, not the request, so the warning must too."""

    request_a = series_request("req-a", sonarr_series_id=99)
    request_b = series_request("req-b", sonarr_series_id=99)
    release_a = make_release("rel-a", files=[series_file("fa", "req-a")], requests=[request_a])
    release_b = make_release("rel-b", files=[series_file("fb", "req-b")], requests=[request_b])

    warnings = ReleaseWarningEvaluator().evaluate([release_a, release_b])

    assert warnings["rel-a"][0].related_release_ids == ["rel-b"]
    assert warnings["rel-b"][0].related_release_ids == ["rel-a"]


def test_two_requests_without_sonarr_series_id_do_not_collide() -> None:
    """Without a resolved arr id, the fallback key is per-request, so distinct
    requests pointing at the same season/episode are not conflated."""

    request_a = series_request("req-a", sonarr_series_id=None)
    request_b = series_request("req-b", sonarr_series_id=None)
    release_a = make_release("rel-a", files=[series_file("fa", "req-a")], requests=[request_a])
    release_b = make_release("rel-b", files=[series_file("fb", "req-b")], requests=[request_b])

    assert ReleaseWarningEvaluator().evaluate([release_a, release_b]) == {}


def test_movie_releases_overlap_on_radarr_movie_id() -> None:
    request_a = movie_request("req-a", radarr_movie_id=7)
    request_b = movie_request("req-b", radarr_movie_id=7)
    release_a = make_release(
        "rel-a",
        files=[make_file("fa", request_id="req-a", mapping_type=MediaType.MOVIE)],
        requests=[request_a],
    )
    release_b = make_release(
        "rel-b",
        files=[make_file("fb", request_id="req-b", mapping_type=MediaType.MOVIE)],
        requests=[request_b],
    )

    warnings = ReleaseWarningEvaluator().evaluate([release_a, release_b])

    assert warnings["rel-a"][0].related_release_ids == ["rel-b"]
    assert warnings["rel-b"][0].related_release_ids == ["rel-a"]


def test_unmapped_files_are_ignored() -> None:
    release = make_release("rel-1", files=[make_file("f1")], requests=[])
    assert ReleaseWarningEvaluator().evaluate([release]) == {}


class FakeReleaseRepositoryForWarnings:
    """Serves whichever release set the test wants for `get_releases_for_requests`."""

    def __init__(self, releases: list[ReleaseRecord]) -> None:
        self._releases = releases

    async def get_releases_for_requests(self, request_ids: list[str]) -> list[ReleaseRecord]:
        wanted = set(request_ids)
        return [release for release in self._releases if wanted & set(release.request_ids)]


class FakeRequestWarningRepository:
    def __init__(self) -> None:
        self.calls: list[tuple[RequestWarningCode, list[str], list[RequestWarningRecord]]] = []

    async def replace_for_requests(
        self,
        code: RequestWarningCode,
        request_ids: list[str],
        warnings: list[RequestWarningRecord],
    ) -> None:
        self.calls.append((code, list(request_ids), list(warnings)))

    async def replace_for_releases(self, code, release_ids, warnings) -> None:
        raise AssertionError("not used in this test")

    async def delete_for_release(self, release_id: str) -> None:
        raise AssertionError("not used in this test")

    async def delete_for_request_release(self, request_id: str, release_id: str) -> None:
        raise AssertionError("not used in this test")

    async def list_for_requests(self, request_ids):
        raise AssertionError("not used in this test")

    async def list_for_releases(self, release_ids):
        raise AssertionError("not used in this test")


async def test_synchronizer_writes_a_row_per_request_sharing_the_release() -> None:
    request = series_request("req-1")
    release_a = make_release("rel-a", files=[series_file("fa", "req-1")], requests=[request])
    release_b = make_release("rel-b", files=[series_file("fb", "req-1")], requests=[request])

    releases_repo = FakeReleaseRepositoryForWarnings([release_a, release_b])
    warning_repo = FakeRequestWarningRepository()
    synchronizer = RequestWarningSynchronizer(releases_repo, warning_repo)

    await synchronizer.sync_for_requests(["req-1"])

    assert len(warning_repo.calls) == 1
    code, request_ids, rows = warning_repo.calls[0]
    assert code is RequestWarningCode.MAPPING_OVERLAP
    assert request_ids == ["req-1"]
    assert {row.release_id for row in rows} == {"rel-a", "rel-b"}
    assert all(row.request_id == "req-1" for row in rows)


async def test_synchronizer_clears_a_release_that_stopped_overlapping() -> None:
    """Three releases on one request, one of which stops overlapping, must lose
    only its own row - the other two keep theirs."""

    request = series_request("req-1")
    release_a = make_release("rel-a", files=[series_file("fa", "req-1", 1, 1)], requests=[request])
    release_b = make_release("rel-b", files=[series_file("fb", "req-1", 1, 1)], requests=[request])
    release_c = make_release("rel-c", files=[series_file("fc", "req-1", 1, 1)], requests=[request])

    releases_repo = FakeReleaseRepositoryForWarnings([release_a, release_b, release_c])
    warning_repo = FakeRequestWarningRepository()
    synchronizer = RequestWarningSynchronizer(releases_repo, warning_repo)

    await synchronizer.sync_for_requests(["req-1"])
    _, _, first_rows = warning_repo.calls[0]
    assert {row.release_id for row in first_rows} == {"rel-a", "rel-b", "rel-c"}

    # release-c's file now maps to a different episode: it no longer overlaps.
    release_c_resolved = make_release(
        "rel-c", files=[series_file("fc", "req-1", 1, 2)], requests=[request]
    )
    releases_repo._releases = [release_a, release_b, release_c_resolved]

    await synchronizer.sync_for_requests(["req-1"])
    _, _, second_rows = warning_repo.calls[1]
    assert {row.release_id for row in second_rows} == {"rel-a", "rel-b"}


async def test_synchronizer_ignores_requests_outside_its_scope() -> None:
    """A release shared with a request outside the recompute scope must not
    write a row for that other request."""

    request_a = series_request("req-a")
    request_b = series_request("req-b", sonarr_series_id=42)
    shared_release = make_release(
        "rel-shared",
        files=[series_file("fa", "req-a"), series_file("fb", "req-b")],
        requests=[request_a, request_b],
    )

    releases_repo = FakeReleaseRepositoryForWarnings([shared_release])
    warning_repo = FakeRequestWarningRepository()
    synchronizer = RequestWarningSynchronizer(releases_repo, warning_repo)

    await synchronizer.sync_for_requests(["req-a"])

    _, request_ids, rows = warning_repo.calls[0]
    assert request_ids == ["req-a"]
    assert all(row.request_id == "req-a" for row in rows)


def test_rows_to_release_warnings_includes_a_regrab_row_alongside_an_overlap_row() -> None:
    """A release card needs both codes, not just the file-mapping one."""

    rows = [
        RequestWarningRecord(
            request_id="req-1",
            release_id="rel-1",
            code=RequestWarningCode.MAPPING_OVERLAP,
            details={"file_ids": ["f1"], "related_release_ids": ["rel-2"]},
        ),
        RequestWarningRecord(
            request_id="req-1",
            release_id="rel-1",
            code=RequestWarningCode.REGRAB_INDEXER_UNAVAILABLE,
            details={"reason": "indexer RuTracker is disabled in Prowlarr"},
        ),
    ]

    warnings = rows_to_release_warnings(rows)

    by_code = {warning.code: warning for warning in warnings}
    assert set(by_code) == {
        RequestWarningCode.MAPPING_OVERLAP,
        RequestWarningCode.REGRAB_INDEXER_UNAVAILABLE,
    }
    assert by_code[RequestWarningCode.MAPPING_OVERLAP].file_ids == ["f1"]
    assert by_code[RequestWarningCode.REGRAB_INDEXER_UNAVAILABLE].file_ids == []
    assert by_code[RequestWarningCode.REGRAB_INDEXER_UNAVAILABLE].related_release_ids == []
    assert (
        by_code[RequestWarningCode.REGRAB_INDEXER_UNAVAILABLE].details["reason"]
        == "indexer RuTracker is disabled in Prowlarr"
    )


def test_rows_to_release_warnings_dedupes_the_same_code_across_requests() -> None:
    """Two rows for the same release/code (one per sharing request) collapse to one."""

    rows = [
        RequestWarningRecord(
            request_id="req-1",
            release_id="rel-1",
            code=RequestWarningCode.REGRAB_INDEXER_UNAVAILABLE,
            details={"reason": "indexer banned"},
        ),
        RequestWarningRecord(
            request_id="req-2",
            release_id="rel-1",
            code=RequestWarningCode.REGRAB_INDEXER_UNAVAILABLE,
            details={"reason": "indexer banned"},
        ),
    ]

    warnings = rows_to_release_warnings(rows)

    assert len(warnings) == 1
