"""Tests for grabbing a release the user supplied by hand."""

from __future__ import annotations

from base64 import b64encode
from datetime import UTC, datetime

import pytest
from torrentool.api import Torrent

from src.application.interfaces.releases import (
    CreateReleaseData,
    FileMappingUpdateData,
    QueuedDownload,
    ReleaseFileRecord,
    ReleaseRecord,
    ReleaseRequestSnapshot,
)
from src.application.use_cases.releases.auto_mapping import ReleaseAutoMapper
from src.application.use_cases.releases.commands import QueueManualReleaseCommand
from src.application.use_cases.releases.exceptions import (
    ExistingReleasesDecisionRequiredError,
    ReleaseDownloadConflictError,
    ReleaseDownloadFailedError,
)
from src.application.use_cases.releases.queue_manual_release import QueueManualReleaseUseCase
from src.application.use_cases.releases.replace_existing import ExistingReleaseReplacer
from src.application.utility.file_matcher import ReleaseFileMatcher
from src.domain.enums import ExistingReleasesAction, MediaType, ReleaseStatus

REQUEST_ID = "req-1"
MAGNET = "magnet:?xt=urn:btih:abc123def4567890abc123def4567890abc123de&dn=Show.S01.1080p"
INFO_HASH = "ABC123DEF4567890ABC123DEF4567890ABC123DE"


def make_release_record(data: CreateReleaseData) -> ReleaseRecord:
    return ReleaseRecord(
        id=data.id,
        name=data.name,
        info_hash=data.id,
        size_bytes=sum(file.size_bytes for file in data.files or []),
        status=ReleaseStatus.PENDING,
        progress=0.0,
        download_speed=0.0,
        upload_speed=0.0,
        seeders=0,
        leechers=0,
        ratio=0.0,
        added_at=datetime.now(UTC),
        completed_at=None,
        request_ids=list(data.request_ids),
        requests=[],
        torrent_source=data.source,
        quality=data.quality,
        files=list(data.files or []),
        last_exported_info_hash=None,
        export_failures_count=0,
    )


class FakeReleaseRepository:
    def __init__(
        self,
        releases: dict[str, ReleaseRecord] | None = None,
        known_requests: dict[str, ReleaseRequestSnapshot] | None = None,
    ) -> None:
        self.releases = releases or {}
        self.known_requests = known_requests or {}
        self.last_created: CreateReleaseData | None = None
        self.last_updates: list[FileMappingUpdateData] | None = None

    async def get_release(self, release_id: str) -> ReleaseRecord | None:
        return self.releases.get(release_id)

    async def delete_release(self, release_id: str) -> bool:
        return self.releases.pop(release_id, None) is not None

    async def unlink_request(self, release_id: str, request_id: str) -> bool:
        record = self.releases.get(release_id)
        if record is None:
            return False
        record.request_ids = [rid for rid in record.request_ids if rid != request_id]
        return True

    async def get_releases_for_requests(self, request_ids: list[str]) -> list[ReleaseRecord]:
        wanted = set(request_ids)
        return [record for record in self.releases.values() if wanted & set(record.request_ids)]

    async def create_release(self, data: CreateReleaseData) -> ReleaseRecord:
        self.last_created = data
        record = make_release_record(data)
        record.requests = [
            self.known_requests[request_id]
            for request_id in data.request_ids
            if request_id in self.known_requests
        ]
        self.releases[data.id] = record
        return record

    async def update_file_mappings(
        self,
        release_id: str,
        updates: list[FileMappingUpdateData],
    ) -> bool:
        self.last_updates = updates
        return release_id in self.releases


class FakeDownloadService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str, bytes | None]] = []
        self.deleted: list[str] = []

    async def delete_download(self, info_hash: str) -> None:
        self.deleted.append(info_hash)

    async def queue_download(
        self,
        request_id: str,
        release_id: str,
        magnet_link: str,
        torrent_bytes: bytes | None = None,
    ) -> QueuedDownload:
        self.calls.append((request_id, release_id, magnet_link, torrent_bytes))
        return QueuedDownload(
            operation="queue_download",
            status="completed",
            operation_id="op-1",
            location=None,
            message=None,
            resource_id=release_id,
            details={"request_id": request_id},
        )


class FailingDownloadService(FakeDownloadService):
    async def queue_download(
        self,
        request_id: str,
        release_id: str,
        magnet_link: str,
        torrent_bytes: bytes | None = None,
    ) -> QueuedDownload:
        raise RuntimeError("client offline")


class FakeRecomputeState:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    async def execute(self, request_ids: list[str]) -> None:
        self.calls.append(list(request_ids))


@pytest.fixture
def season_pack(tmp_path) -> bytes:
    directory = tmp_path / "Avatar.S01.1080p.BluRay.x264"
    directory.mkdir()
    (directory / "Avatar.S01E01.mkv").write_bytes(b"a" * 2048)
    (directory / "Avatar.S01E02.mkv").write_bytes(b"b" * 2048)
    return Torrent.create_from(directory).to_string()


def series_snapshot() -> ReleaseRequestSnapshot:
    return ReleaseRequestSnapshot(
        id=REQUEST_ID,
        sonarr_series_id=42,
        title="Avatar: The Last Airbender - Season 1",
        media_type=MediaType.SERIES,
        season_number=1,
    )


@pytest.mark.asyncio
async def test_uploaded_torrent_is_queued_with_its_bytes(season_pack: bytes) -> None:
    repository = FakeReleaseRepository()
    download_service = FakeDownloadService()
    use_case = QueueManualReleaseUseCase(repository, download_service)

    result = await use_case.execute(
        QueueManualReleaseCommand(
            request_id=REQUEST_ID,
            torrent_file_base64=b64encode(season_pack).decode(),
        )
    )

    assert result.operation == "queue_download"
    request_id, release_id, magnet_link, torrent_bytes = download_service.calls[0]
    assert request_id == REQUEST_ID
    # The download client gets the file itself, so it never has to fetch
    # metadata from the swarm before it can start.
    assert torrent_bytes == season_pack
    assert magnet_link.startswith("magnet:?xt=urn:btih:")

    created = repository.last_created
    assert created is not None
    assert created.id == release_id
    assert created.name == "Avatar.S01.1080p.BluRay.x264"
    assert created.source == "manual"
    assert [file.name for file in created.files or []] == [
        "Avatar.S01.1080p.BluRay.x264/Avatar.S01E01.mkv",
        "Avatar.S01.1080p.BluRay.x264/Avatar.S01E02.mkv",
    ]


@pytest.mark.asyncio
async def test_magnet_is_queued_without_a_file_list() -> None:
    repository = FakeReleaseRepository()
    download_service = FakeDownloadService()
    use_case = QueueManualReleaseUseCase(repository, download_service)

    await use_case.execute(QueueManualReleaseCommand(request_id=REQUEST_ID, magnet_link=MAGNET))

    assert download_service.calls == [(REQUEST_ID, INFO_HASH, MAGNET, None)]
    created = repository.last_created
    assert created is not None
    assert created.id == INFO_HASH
    # Only the download client learns the file names, and only once it has the
    # metadata, so there is nothing to record or map yet.
    assert created.files is None
    assert created.name == "Show.S01.1080p"


@pytest.mark.asyncio
async def test_uploaded_torrent_files_are_mapped_on_arrival(season_pack: bytes) -> None:
    repository = FakeReleaseRepository(known_requests={REQUEST_ID: series_snapshot()})
    use_case = QueueManualReleaseUseCase(
        repository,
        FakeDownloadService(),
        auto_mapper=ReleaseAutoMapper(repository, ReleaseFileMatcher()),
    )

    await use_case.execute(
        QueueManualReleaseCommand(
            request_id=REQUEST_ID,
            torrent_file_base64=b64encode(season_pack).decode(),
        )
    )

    assert repository.last_updates is not None
    assert [
        (update.mapping.request_id, update.mapping.season, update.mapping.episode)
        for update in repository.last_updates
        if update.mapping is not None
    ] == [(REQUEST_ID, 1, 1), (REQUEST_ID, 1, 2)]


@pytest.mark.asyncio
async def test_grab_settles_request_state() -> None:
    recompute_state = FakeRecomputeState()
    use_case = QueueManualReleaseUseCase(
        FakeReleaseRepository(),
        FakeDownloadService(),
        recompute_state=recompute_state,
    )

    await use_case.execute(QueueManualReleaseCommand(request_id=REQUEST_ID, magnet_link=MAGNET))

    assert recompute_state.calls == [[REQUEST_ID]]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "command",
    [
        QueueManualReleaseCommand(request_id=REQUEST_ID),
        QueueManualReleaseCommand(request_id=REQUEST_ID, magnet_link="   "),
        QueueManualReleaseCommand(
            request_id=REQUEST_ID,
            magnet_link=MAGNET,
            torrent_file_base64=b64encode(b"d4:spami42ee").decode(),
        ),
        QueueManualReleaseCommand(request_id=REQUEST_ID, magnet_link="https://example.test/x"),
        QueueManualReleaseCommand(request_id=REQUEST_ID, torrent_file_base64="not base64!"),
        QueueManualReleaseCommand(
            request_id=REQUEST_ID,
            torrent_file_base64=b64encode(b"not a torrent").decode(),
        ),
        QueueManualReleaseCommand(request_id="", magnet_link=MAGNET),
    ],
)
async def test_unusable_payloads_are_rejected(command: QueueManualReleaseCommand) -> None:
    download_service = FakeDownloadService()
    use_case = QueueManualReleaseUseCase(FakeReleaseRepository(), download_service)

    with pytest.raises(ValueError):
        await use_case.execute(command)

    assert download_service.calls == []


@pytest.mark.asyncio
async def test_a_release_already_registered_is_a_conflict() -> None:
    existing = make_release_record(
        CreateReleaseData(
            magnet_link=MAGNET,
            request_ids=[REQUEST_ID],
            name="Show.S01.1080p",
            id=INFO_HASH,
            source="manual",
            quality="",
        )
    )
    download_service = FakeDownloadService()
    use_case = QueueManualReleaseUseCase(
        FakeReleaseRepository({existing.id: existing}), download_service
    )

    with pytest.raises(ReleaseDownloadConflictError):
        await use_case.execute(QueueManualReleaseCommand(request_id=REQUEST_ID, magnet_link=MAGNET))

    assert download_service.calls == []


@pytest.mark.asyncio
async def test_a_download_client_failure_surfaces() -> None:
    repository = FakeReleaseRepository()
    use_case = QueueManualReleaseUseCase(repository, FailingDownloadService())

    with pytest.raises(ReleaseDownloadFailedError):
        await use_case.execute(QueueManualReleaseCommand(request_id=REQUEST_ID, magnet_link=MAGNET))

    # Nothing was queued, so the release must not be left behind as a record.
    assert repository.last_created is None


@pytest.mark.asyncio
async def test_unnamed_magnet_falls_back_to_its_info_hash() -> None:
    repository = FakeReleaseRepository()
    use_case = QueueManualReleaseUseCase(repository, FakeDownloadService())

    await use_case.execute(
        QueueManualReleaseCommand(
            request_id=REQUEST_ID,
            magnet_link=f"magnet:?xt=urn:btih:{INFO_HASH}",
        )
    )

    created = repository.last_created
    assert created is not None
    assert created.name == INFO_HASH


def test_release_file_records_get_distinct_ids(season_pack: bytes) -> None:
    """Mapping updates address files by id, so duplicates would collide."""

    from src.application.use_cases.releases.grab import to_release_files
    from src.application.utility.torrent import parse_torrent

    files: list[ReleaseFileRecord] = to_release_files(parse_torrent(season_pack).files)

    assert len({file.id for file in files}) == len(files)


@pytest.mark.asyncio
async def test_manual_grab_requires_decision_when_request_has_releases() -> None:
    existing = make_release_record(
        CreateReleaseData(
            magnet_link=MAGNET,
            request_ids=[REQUEST_ID],
            name="Show.S01.1080p",
            id=INFO_HASH,
            source="manual",
            quality="",
        )
    )
    repository = FakeReleaseRepository({existing.id: existing})
    download_service = FakeDownloadService()
    replacer = ExistingReleaseReplacer(repository, download_service)
    use_case = QueueManualReleaseUseCase(
        repository, download_service, existing_release_replacer=replacer
    )

    other_magnet = "magnet:?xt=urn:btih:1112223334445556667778889990001112223334"
    with pytest.raises(ExistingReleasesDecisionRequiredError) as exc_info:
        await use_case.execute(
            QueueManualReleaseCommand(request_id=REQUEST_ID, magnet_link=other_magnet)
        )

    assert exc_info.value.release_ids == [existing.id]
    assert download_service.calls == []


@pytest.mark.asyncio
async def test_manual_grab_replace_deletes_exclusive_release() -> None:
    existing = make_release_record(
        CreateReleaseData(
            magnet_link=MAGNET,
            request_ids=[REQUEST_ID],
            name="Show.S01.1080p",
            id=INFO_HASH,
            source="manual",
            quality="",
        )
    )
    repository = FakeReleaseRepository({existing.id: existing})
    download_service = FakeDownloadService()
    replacer = ExistingReleaseReplacer(repository, download_service)
    use_case = QueueManualReleaseUseCase(
        repository, download_service, existing_release_replacer=replacer
    )

    other_magnet = "magnet:?xt=urn:btih:1112223334445556667778889990001112223334"
    await use_case.execute(
        QueueManualReleaseCommand(
            request_id=REQUEST_ID,
            magnet_link=other_magnet,
            existing_releases=ExistingReleasesAction.REPLACE,
        )
    )

    assert existing.id not in repository.releases
    assert download_service.deleted == [existing.info_hash]
