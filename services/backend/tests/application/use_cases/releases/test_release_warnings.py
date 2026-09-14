"""Unit tests for ReleaseWarningEvaluator."""

from __future__ import annotations

from datetime import UTC, datetime

from src.application.interfaces.releases import (
    ReleaseFileMapping,
    ReleaseFileRecord,
    ReleaseRecord,
    ReleaseRequestSnapshot,
)
from src.application.use_cases.releases.warnings import ReleaseWarningEvaluator
from src.domain.enums import MediaType, ReleaseStatus, ReleaseWarningCode


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
    assert warnings["rel-1"][0].code is ReleaseWarningCode.MAPPING_OVERLAP
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
