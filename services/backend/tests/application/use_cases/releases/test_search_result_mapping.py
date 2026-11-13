"""Tests for what a release search hands back to the caller."""

from __future__ import annotations

from src.application.interfaces.releases import ReleaseSearchResultRecord, ReleaseSearchResults
from src.application.use_cases.releases.mappers import search_results_to_dto

PROWLARR_LINK = "https://prowlarr.test/13/download?apikey=SECRET&link=opaque&file=Show"


def record(*, magnet_link: str | None, torrent_file_url: str | None) -> ReleaseSearchResultRecord:
    return ReleaseSearchResultRecord(
        release_id="rel-1",
        release_name="Show",
        size="1 GB",
        magnet_link=magnet_link,
        torrent_file_url=torrent_file_url,
        info_url="https://tracker.test/t/1",
        seeders=1,
        leechers=0,
        quality=None,
        source="Indexer",
        request_id=None,
    )


def mapped(result: ReleaseSearchResultRecord):
    results = ReleaseSearchResults(results=[result], query="q", total_results=1)
    return search_results_to_dto(results).results[0]


def test_prowlarr_links_never_reach_the_caller() -> None:
    dto = mapped(record(magnet_link=PROWLARR_LINK, torrent_file_url=PROWLARR_LINK))

    assert dto.magnet_link is None
    assert dto.has_torrent_file is True
    assert "SECRET" not in repr(dto)


def test_a_real_magnet_is_passed_on() -> None:
    dto = mapped(record(magnet_link="magnet:?xt=urn:btih:ABC", torrent_file_url=None))

    assert dto.magnet_link == "magnet:?xt=urn:btih:ABC"
    assert dto.has_torrent_file is False
