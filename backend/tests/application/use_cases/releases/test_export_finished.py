"""Tests for exporting finished releases, including multi-season packs."""

from __future__ import annotations

from datetime import UTC, datetime

from src.application.interfaces.media_requests import (
    MediaRequestRecord,
    UpdateMediaRequestData,
)
from src.application.interfaces.releases import (
    FileMappingUpdateData,
    ReleaseFileRecord,
    ReleaseRecord,
    ReleaseRequestSnapshot,
)
from src.application.interfaces.sonarr import (
    ManualImportFile,
    SeriesDetails,
    SeriesSeasonDetails,
    SonarrEpisode,
)
from src.application.use_cases.releases.export_finished import ExportFinishedSeriesUseCase
from src.application.utility.file_matcher import ReleaseFileMatcher
from src.domain.enums import MediaRequestStatus, MediaType, ReleaseStatus

SERIES_ID = 42
DOWNLOAD_DIR = "/media/downloads"
EPISODES_PER_SEASON = 20


def make_request_record(request_id: str, season: int) -> MediaRequestRecord:
    now = datetime.now(UTC)
    return MediaRequestRecord(
        id=request_id,
        media_type=MediaType.SERIES,
        status=MediaRequestStatus.DOWNLOADING,
        title=f"Avatar: The Last Airbender - Season {season}",
        year=2005,
        overview=None,
        poster_url=None,
        genres=[],
        runtime_minutes=None,
        imdb_id="tt0417299",
        season_number=season,
        total_episodes=20,
        series_title="Avatar: The Last Airbender",
        series_year=2005,
        created_at=now,
        updated_at=now,
        sonarr_series_id=SERIES_ID,
    )


def make_release(files: list[ReleaseFileRecord], season: int) -> ReleaseRecord:
    now = datetime.now(UTC)
    return ReleaseRecord(
        id="rel-1",
        name="Avatar.The.Last.Airbender.COMPLETE.S01-S03.1080p.BluRay.x264",
        info_hash="hash-1",
        size_bytes=1024,
        status=ReleaseStatus.COMPLETED,
        progress=1.0,
        download_speed=0.0,
        upload_speed=0.0,
        seeders=1,
        leechers=0,
        ratio=1.0,
        added_at=now,
        completed_at=now,
        request_ids=[f"req-{season}"],
        requests=[
            ReleaseRequestSnapshot(
                id=f"req-{season}",
                sonarr_series_id=SERIES_ID,
                title=f"Avatar: The Last Airbender - Season {season}",
                media_type=MediaType.SERIES,
                season_number=season,
            )
        ],
        torrent_source="prowlarr",
        quality="1080p",
        files=files,
        last_exported_info_hash=None,
        export_failures_count=0,
    )


def make_file(file_id: str, path: str) -> ReleaseFileRecord:
    return ReleaseFileRecord(
        id=file_id,
        name=path.rsplit("/", 1)[-1],
        size_bytes=2048,
        path=path,
        mapping=None,
    )


class FakeReleaseRepository:
    def __init__(self, release: ReleaseRecord) -> None:
        self.release = release
        self.mapping_updates: list[FileMappingUpdateData] = []
        self.release_updates: dict[str, object] = {}

    async def get_finished_not_exported(self) -> list[ReleaseRecord]:
        return [self.release]

    async def update_file_mappings(
        self,
        release_id: str,
        updates: list[FileMappingUpdateData],
    ) -> bool:
        self.mapping_updates.extend(updates)
        return True

    async def update_release(self, release_id: str, **kwargs: object) -> bool:
        self.release_updates.update(kwargs)
        return True


class FakeMediaRequestRepository:
    def __init__(self, records: list[MediaRequestRecord]) -> None:
        self.records = records
        self.lookups: list[tuple[int, int]] = []
        self.updates: list[tuple[str, UpdateMediaRequestData]] = []

    async def find_by_sonarr(
        self,
        *,
        sonarr_series_id: int,
        season_number: int,
    ) -> MediaRequestRecord | None:
        self.lookups.append((sonarr_series_id, season_number))
        return next(
            (
                record
                for record in self.records
                if record.sonarr_series_id == sonarr_series_id
                and record.season_number == season_number
            ),
            None,
        )

    async def update_request(
        self,
        request_id: str,
        data: UpdateMediaRequestData,
    ) -> MediaRequestRecord | None:
        self.updates.append((request_id, data))
        return None


class FakeDownloadService:
    def __init__(self, directory: str | None = DOWNLOAD_DIR) -> None:
        self.directory = directory
        self.lookups: list[str] = []

    async def get_download_directory(self, info_hash: str) -> str | None:
        self.lookups.append(info_hash)
        return self.directory


class FakeSonarrService:
    def __init__(self, files_per_season: dict[int, int] | None = None) -> None:
        self.imported: list[ManualImportFile] = []
        self.files_per_season = files_per_season or dict.fromkeys((1, 2, 3), EPISODES_PER_SEASON)

    async def get_episodes(self, series_id: int) -> list[SonarrEpisode]:
        return [
            SonarrEpisode(
                id=season * 100 + episode,
                season_number=season,
                episode_number=episode,
            )
            for season in (1, 2, 3)
            for episode in range(1, EPISODES_PER_SEASON + 1)
        ]

    async def get_series(self, series_id: int) -> SeriesDetails:
        return SeriesDetails(
            id=series_id,
            title="Avatar: The Last Airbender",
            year=2005,
            overview=None,
            poster_url=None,
            imdb_id="tt0417299",
            tvdb_id=74852,
            genres=[],
            seasons={
                season: SeriesSeasonDetails(
                    season_number=season,
                    episode_count=EPISODES_PER_SEASON,
                    total_episode_count=EPISODES_PER_SEASON,
                    episode_file_count=self.files_per_season.get(season, 0),
                )
                for season in (1, 2, 3)
            },
        )

    async def manual_import(self, files: list[ManualImportFile]) -> bool:
        self.imported.extend(files)
        return True


def build_use_case(
    release: ReleaseRecord,
    requests: list[MediaRequestRecord],
    request_repository: FakeMediaRequestRepository | None = None,
    sonarr: FakeSonarrService | None = None,
) -> tuple[ExportFinishedSeriesUseCase, FakeReleaseRepository, FakeSonarrService]:
    repository = FakeReleaseRepository(release)
    sonarr = sonarr or FakeSonarrService()
    use_case = ExportFinishedSeriesUseCase(
        repository=repository,  # type: ignore[arg-type]
        sonarr=sonarr,  # type: ignore[arg-type]
        file_matcher=ReleaseFileMatcher(),
        download_service=FakeDownloadService(),  # type: ignore[arg-type]
        request_repository=request_repository  # type: ignore[arg-type]
        or FakeMediaRequestRepository(requests),
    )
    return use_case, repository, sonarr


async def test_multi_season_pack_maps_each_season_to_its_own_request() -> None:
    """Grabbing a complete-series pack from one season must still fill the others."""

    files = [
        make_file("f1", "Avatar/Avatar.S01E01.mkv"),
        make_file("f2", "Avatar/Avatar.S02E01.mkv"),
        make_file("f3", "Avatar/Avatar.S03E01.mkv"),
    ]
    release = make_release(files, season=1)
    requests = [make_request_record("req-2", 2), make_request_record("req-3", 3)]

    use_case, repository, sonarr = build_use_case(release, requests)
    result = await use_case.execute()

    assert result.succeeded == 1
    assert {
        update.file_id: (update.mapping.request_id, update.mapping.season)
        for update in repository.mapping_updates
        if update.mapping is not None
    } == {
        "f1": ("req-1", 1),
        "f2": ("req-2", 2),
        "f3": ("req-3", 3),
    }
    assert [(item.path, item.episode_ids) for item in sonarr.imported] == [
        (f"{DOWNLOAD_DIR}/Avatar/Avatar.S01E01.mkv", [101]),
        (f"{DOWNLOAD_DIR}/Avatar/Avatar.S02E01.mkv", [201]),
        (f"{DOWNLOAD_DIR}/Avatar/Avatar.S03E01.mkv", [301]),
    ]
    assert repository.release_updates["last_exported_info_hash"] == "hash-1"


async def test_exported_seasons_are_marked_completed() -> None:
    """The finished-download sequence skips the Sonarr sync that would do this."""

    files = [
        make_file("f1", "Avatar/Avatar.S01E01.mkv"),
        make_file("f2", "Avatar/Avatar.S02E01.mkv"),
    ]
    request_repository = FakeMediaRequestRepository([make_request_record("req-2", 2)])

    use_case, _, _ = build_use_case(make_release(files, season=1), [], request_repository)
    await use_case.execute()

    assert [(request_id, data.status) for request_id, data in request_repository.updates] == [
        ("req-1", MediaRequestStatus.COMPLETED),
        ("req-2", MediaRequestStatus.COMPLETED),
    ]


async def test_a_season_sonarr_still_wants_more_of_stays_in_flight() -> None:
    """A release carrying part of a season must not close the request."""

    files = [make_file("f1", "Avatar/Avatar.S01E01.mkv")]
    request_repository = FakeMediaRequestRepository([])
    sonarr = FakeSonarrService(files_per_season={1: EPISODES_PER_SEASON - 5})

    use_case, repository, _ = build_use_case(
        make_release(files, season=1),
        [],
        request_repository,
        sonarr,
    )
    await use_case.execute()

    assert repository.release_updates["last_exported_info_hash"] == "hash-1"
    assert request_repository.updates == []


async def test_only_seasons_present_in_the_release_are_looked_up() -> None:
    files = [make_file("f1", "Avatar/Avatar.S03E05.mkv")]
    request_repository = FakeMediaRequestRepository([make_request_record("req-3", 3)])

    use_case, _, _ = build_use_case(make_release(files, season=1), [], request_repository)
    await use_case.execute()

    assert request_repository.lookups == [(SERIES_ID, 3)]


async def test_release_stays_unexported_when_nothing_could_be_mapped() -> None:
    files = [make_file("f1", "Avatar/Avatar.S04E01.mkv")]
    release = make_release(files, season=1)

    use_case, repository, sonarr = build_use_case(release, [])
    result = await use_case.execute()

    assert result.succeeded == 1
    assert sonarr.imported == []
    assert repository.release_updates == {}


async def test_release_stays_unexported_when_the_download_directory_is_unknown() -> None:
    """Sonarr resolves paths on its own filesystem, so a relative path is useless."""

    release = make_release([make_file("f1", "Avatar/Avatar.S01E01.mkv")], season=1)
    repository = FakeReleaseRepository(release)
    sonarr = FakeSonarrService()
    use_case = ExportFinishedSeriesUseCase(
        repository=repository,  # type: ignore[arg-type]
        sonarr=sonarr,  # type: ignore[arg-type]
        file_matcher=ReleaseFileMatcher(),
        download_service=FakeDownloadService(None),  # type: ignore[arg-type]
        request_repository=FakeMediaRequestRepository([]),  # type: ignore[arg-type]
    )

    result = await use_case.execute()

    assert result.succeeded == 1
    assert sonarr.imported == []
    assert repository.release_updates == {}
