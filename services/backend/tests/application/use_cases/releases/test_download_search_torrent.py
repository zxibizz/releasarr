"""Tests for handing a search result's .torrent file to the caller."""

from __future__ import annotations

import pytest
from torrentool.api import Torrent

from src.application.interfaces.releases import ReleaseSearchResultRecord, TorrentFetchError
from src.application.use_cases.indexers.exceptions import ProwlarrNotConfiguredError
from src.application.use_cases.releases.download_search_torrent import (
    DownloadSearchTorrentUseCase,
)
from src.application.use_cases.releases.exceptions import (
    ReleaseNotFoundError,
    ReleaseTorrentUnavailableError,
)
from tests.fakes import InMemoryReleaseSearchService


def result(release_id: str = "rel-1", *, torrent_file_url: str | None) -> ReleaseSearchResultRecord:
    return ReleaseSearchResultRecord(
        release_id=release_id,
        release_name="Indexer: Title / 1080p",
        size="1 GB",
        magnet_link=None,
        torrent_file_url=torrent_file_url,
        info_url=None,
        seeders=1,
        leechers=0,
        quality=None,
        source="Indexer",
        request_id="req-1",
    )


@pytest.fixture
def torrent_bytes(tmp_path) -> bytes:
    directory = tmp_path / 'Show: "S01" 1080p'
    directory.mkdir()
    (directory / "Show.S01E01.mkv").write_bytes(b"a" * 2048)
    return Torrent.create_from(directory).to_string()


def service_with(record: ReleaseSearchResultRecord) -> InMemoryReleaseSearchService:
    service = InMemoryReleaseSearchService()
    service.register_results("q", request_id="req-1", results=[record])
    return service


async def test_returns_the_torrent_named_after_its_own_name(torrent_bytes: bytes) -> None:
    service = service_with(result(torrent_file_url="memory://rel-1"))
    service.register_torrent("rel-1", torrent_bytes)

    dto = await DownloadSearchTorrentUseCase(service).execute("rel-1")

    assert dto.content == torrent_bytes
    # The torrent's own name, with what a filesystem or a header cannot take replaced.
    assert dto.filename == "Show_ _S01_ 1080p.torrent"


async def test_an_unknown_result_is_not_found() -> None:
    service = service_with(result(torrent_file_url="memory://rel-1"))

    with pytest.raises(ReleaseNotFoundError):
        await DownloadSearchTorrentUseCase(service).execute("rel-2")


async def test_a_magnet_only_result_has_no_torrent() -> None:
    service = service_with(result(torrent_file_url=None))

    with pytest.raises(ReleaseTorrentUnavailableError):
        await DownloadSearchTorrentUseCase(service).execute("rel-1")


async def test_a_failed_fetch_propagates() -> None:
    service = service_with(result(torrent_file_url="memory://rel-1"))

    with pytest.raises(TorrentFetchError):
        await DownloadSearchTorrentUseCase(service).execute("rel-1")


async def test_an_answer_that_is_not_a_torrent_is_not_passed_on() -> None:
    service = service_with(result(torrent_file_url="memory://rel-1"))
    service.register_torrent("rel-1", b"<html>indexer error</html>")

    with pytest.raises(TorrentFetchError):
        await DownloadSearchTorrentUseCase(service).execute("rel-1")


async def test_an_unconfigured_prowlarr_is_reported() -> None:
    service = service_with(result(torrent_file_url="memory://rel-1"))
    service.is_configured = False  # type: ignore[misc]

    with pytest.raises(ProwlarrNotConfiguredError):
        await DownloadSearchTorrentUseCase(service).execute("rel-1")
