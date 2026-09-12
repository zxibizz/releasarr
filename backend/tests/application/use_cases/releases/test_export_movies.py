"""Tests for exporting finished movie releases into Radarr."""

from __future__ import annotations

from datetime import UTC, datetime

from src.application.interfaces.media_requests import (
    MediaRequestRecord,
    UpdateMediaRequestData,
)
from src.application.interfaces.radarr import MovieDetails, MovieImportFile
from src.application.interfaces.releases import (
    FileMappingUpdateData,
    ReleaseFileRecord,
    ReleaseRecord,
    ReleaseRequestSnapshot,
)
from src.application.interfaces.sonarr import ManualImportFile, SeriesDetails, SonarrEpisode
from src.application.use_cases.releases.auto_mapping import ReleaseAutoMapper
from src.application.use_cases.releases.export_finished import ExportFinishedReleasesUseCase
from src.application.utility.file_matcher import ReleaseFileMatcher
from src.domain.enums import MediaRequestStatus, MediaType, ReleaseStatus

MOVIE_ID = 156
DOWNLOAD_DIR = "/media/downloads"


def make_snapshot(request_id: str, movie_id: int, title: str) -> ReleaseRequestSnapshot:
    return ReleaseRequestSnapshot(
        id=request_id,
        sonarr_series_id=None,
        title=title,
        media_type=MediaType.MOVIE,
        season_number=None,
        radarr_movie_id=movie_id,
        year=2016,
    )


def make_record(request_id: str, movie_id: int, title: str) -> MediaRequestRecord:
    now = datetime.now(UTC)
    return MediaRequestRecord(
        id=request_id,
        media_type=MediaType.MOVIE,
        status=MediaRequestStatus.DOWNLOADING,
        title=title,
        year=2016,
        overview=None,
        poster_url=None,
        genres=[],
        runtime_minutes=116,
        imdb_id=None,
        season_number=None,
        total_episodes=None,
        series_title=None,
        series_year=None,
        radarr_movie_id=movie_id,
        created_at=now,
        updated_at=now,
        localizations={},
    )


def make_file(file_id: str, path: str, size_bytes: int = 8_000_000_000) -> ReleaseFileRecord:
    return ReleaseFileRecord(
        id=file_id,
        name=path.rsplit("/", 1)[-1],
        size_bytes=size_bytes,
        path=path,
        mapping=None,
    )


def make_release(
    files: list[ReleaseFileRecord],
    requests: list[ReleaseRequestSnapshot],
    name: str = "Arrival.2016.1080p.BluRay.x264",
) -> ReleaseRecord:
    now = datetime.now(UTC)
    return ReleaseRecord(
        id="rel-1",
        name=name,
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
        request_ids=[request.id for request in requests],
        requests=requests,
        torrent_source="prowlarr",
        quality="1080p",
        files=files,
        last_exported_info_hash=None,
        export_failures_count=0,
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
    def __init__(self, records: list[MediaRequestRecord] | None = None) -> None:
        self.records = records or []
        self.updates: list[tuple[str, UpdateMediaRequestData]] = []

    async def find_by_sonarr(self, **kwargs: object) -> MediaRequestRecord | None:
        return None

    async def list_radarr_requests(self) -> list[MediaRequestRecord]:
        return list(self.records)

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

    async def get_download_directory(self, info_hash: str) -> str | None:
        return self.directory


class FakeRadarrService:
    def __init__(self, has_file: bool = True, succeeds: bool = True) -> None:
        self.imported: list[MovieImportFile] = []
        self.has_file = has_file
        self.succeeds = succeeds

    async def get_missing_movies(self) -> list[MovieDetails]:
        return []

    async def get_movie(self, movie_id: int) -> MovieDetails:
        return MovieDetails(
            id=movie_id,
            title="Arrival",
            year=2016,
            overview=None,
            poster_url=None,
            imdb_id=None,
            tmdb_id=None,
            has_file=self.has_file,
        )

    async def manual_import(self, files: list[MovieImportFile]) -> bool:
        if not self.succeeds:
            return False
        self.imported.extend(files)
        return True


class FakeSonarrService:
    async def get_episodes(self, series_id: int) -> list[SonarrEpisode]:
        return []

    async def get_series(self, series_id: int) -> SeriesDetails:
        raise AssertionError("a movie release must not consult Sonarr")

    async def manual_import(self, files: list[ManualImportFile]) -> bool:
        raise AssertionError("a movie release must not import into Sonarr")


def build_use_case(
    release: ReleaseRecord,
    request_repository: FakeMediaRequestRepository,
    radarr: FakeRadarrService | None = None,
    download_service: FakeDownloadService | None = None,
) -> tuple[ExportFinishedReleasesUseCase, FakeReleaseRepository, FakeRadarrService]:
    repository = FakeReleaseRepository(release)
    radarr = radarr or FakeRadarrService()
    use_case = ExportFinishedReleasesUseCase(
        repository=repository,  # type: ignore[arg-type]
        sonarr=FakeSonarrService(),  # type: ignore[arg-type]
        radarr=radarr,  # type: ignore[arg-type]
        auto_mapper=ReleaseAutoMapper(
            repository=repository,  # type: ignore[arg-type]
            file_matcher=ReleaseFileMatcher(),
            request_repository=request_repository,  # type: ignore[arg-type]
        ),
        download_service=download_service or FakeDownloadService(),  # type: ignore[arg-type]
        request_repository=request_repository,  # type: ignore[arg-type]
    )
    return use_case, repository, radarr


async def test_a_movie_release_is_imported_into_radarr_and_closed() -> None:
    files = [make_file("f1", "Arrival.2016.1080p/arrival.2016.1080p.mkv")]
    release = make_release(files, [make_snapshot("req-1", MOVIE_ID, "Arrival")])
    request_repository = FakeMediaRequestRepository()

    use_case, repository, radarr = build_use_case(release, request_repository)
    result = await use_case.execute()

    assert result.succeeded == 1
    assert [(item.path, item.movie_id, item.folder_name) for item in radarr.imported] == [
        (
            f"{DOWNLOAD_DIR}/Arrival.2016.1080p/arrival.2016.1080p.mkv",
            MOVIE_ID,
            "Arrival.2016.1080p.BluRay.x264",
        )
    ]
    assert repository.release_updates["last_exported_info_hash"] == "hash-1"
    assert request_repository.updates == [
        ("req-1", UpdateMediaRequestData(status=MediaRequestStatus.COMPLETED))
    ]


async def test_only_the_feature_is_imported_not_the_extras() -> None:
    files = [
        make_file("f1", "Arrival.2016/Sample/sample.mkv", 30_000_000),
        make_file("f2", "Arrival.2016/arrival.2016.1080p.mkv", 8_000_000_000),
    ]
    release = make_release(files, [make_snapshot("req-1", MOVIE_ID, "Arrival")])

    use_case, _, radarr = build_use_case(release, FakeMediaRequestRepository())
    await use_case.execute()

    assert [item.path for item in radarr.imported] == [
        f"{DOWNLOAD_DIR}/Arrival.2016/arrival.2016.1080p.mkv"
    ]


async def test_a_movie_radarr_has_not_taken_yet_stays_in_flight() -> None:
    """Radarr is asked to confirm rather than trusting the import command."""

    files = [make_file("f1", "Arrival.2016.1080p/arrival.2016.1080p.mkv")]
    release = make_release(files, [make_snapshot("req-1", MOVIE_ID, "Arrival")])
    request_repository = FakeMediaRequestRepository()

    use_case, repository, _ = build_use_case(
        release,
        request_repository,
        FakeRadarrService(has_file=False),
    )
    await use_case.execute()

    assert repository.release_updates["last_exported_info_hash"] == "hash-1"
    assert request_repository.updates == []


async def test_a_failed_radarr_import_leaves_the_release_unexported() -> None:
    files = [make_file("f1", "Arrival.2016.1080p/arrival.2016.1080p.mkv")]
    release = make_release(files, [make_snapshot("req-1", MOVIE_ID, "Arrival")])

    use_case, repository, _ = build_use_case(
        release,
        FakeMediaRequestRepository(),
        FakeRadarrService(succeeds=False),
    )
    result = await use_case.execute()

    assert result.failed == 1
    assert "last_exported_info_hash" not in repository.release_updates
    assert repository.release_updates["export_failures_count"] == 1


async def test_a_collection_pack_is_split_across_the_movies_it_covers() -> None:
    """The grab names one movie; the siblings come from Radarr's wanted list."""

    files = [
        make_file("f1", "Nolan/Inception.2010.1080p.mkv"),
        make_file("f2", "Nolan/Tenet.2020.1080p.mkv"),
    ]
    release = make_release(
        files,
        [make_snapshot("req-1", 1, "Inception")],
        name="Christopher.Nolan.Collection.1080p",
    )
    request_repository = FakeMediaRequestRepository([make_record("req-2", 2, "Tenet")])

    use_case, _, radarr = build_use_case(release, request_repository)
    await use_case.execute()

    assert [(item.path, item.movie_id) for item in radarr.imported] == [
        (f"{DOWNLOAD_DIR}/Nolan/Inception.2010.1080p.mkv", 1),
        (f"{DOWNLOAD_DIR}/Nolan/Tenet.2020.1080p.mkv", 2),
    ]
    assert sorted(request_id for request_id, _ in request_repository.updates) == ["req-1", "req-2"]


async def test_a_movie_release_stays_unexported_without_a_download_directory() -> None:
    files = [make_file("f1", "Arrival.2016.1080p/arrival.2016.1080p.mkv")]
    release = make_release(files, [make_snapshot("req-1", MOVIE_ID, "Arrival")])

    use_case, repository, radarr = build_use_case(
        release,
        FakeMediaRequestRepository(),
        download_service=FakeDownloadService(None),
    )
    result = await use_case.execute()

    assert result.succeeded == 1
    assert radarr.imported == []
    assert repository.release_updates == {}
