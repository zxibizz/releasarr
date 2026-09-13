"""Tests for reading uploaded torrent payloads."""

from __future__ import annotations

from base64 import b64encode

import pytest
from torrentool.api import Torrent

from src.application.utility.magnet import parse_magnet
from src.application.utility.torrent import (
    TorrentFileInfo,
    decode_torrent_base64,
    parse_torrent,
)


@pytest.fixture
def torrent_bytes(tmp_path) -> bytes:
    """A season pack, which is the shape the file mapping actually cares about."""

    directory = tmp_path / "Show.S01.1080p.WEB-DL"
    directory.mkdir()
    (directory / "Show.S01E01.mkv").write_bytes(b"x" * 4096)
    (directory / "Show.S01E02.mkv").write_bytes(b"y" * 2048)
    return Torrent.create_from(directory).to_string()


def test_decode_torrent_base64_returns_raw_bytes() -> None:
    assert decode_torrent_base64(b64encode(b"d4:spami42ee").decode()) == b"d4:spami42ee"


def test_decode_torrent_base64_accepts_a_data_url() -> None:
    encoded = b64encode(b"d4:spami42ee").decode()

    assert decode_torrent_base64(f"data:application/x-bittorrent;base64,{encoded}") == (
        b"d4:spami42ee"
    )


@pytest.mark.parametrize("value", ["", "   ", "not base64 at all!", b64encode(b"").decode()])
def test_decode_torrent_base64_rejects_unusable_input(value: str) -> None:
    with pytest.raises(ValueError):
        decode_torrent_base64(value)


def test_parse_torrent_reads_magnet_and_files(torrent_bytes: bytes) -> None:
    info = parse_torrent(torrent_bytes)

    assert info.name == "Show.S01.1080p.WEB-DL"
    assert sorted(info.files, key=lambda file: file.name) == [
        TorrentFileInfo(name="Show.S01.1080p.WEB-DL/Show.S01E01.mkv", size_bytes=4096),
        TorrentFileInfo(name="Show.S01.1080p.WEB-DL/Show.S01E02.mkv", size_bytes=2048),
    ]
    # The derived magnet is what the grab hands to the download client, so it
    # has to carry an info hash the same way a pasted one does.
    assert parse_magnet(info.magnet_link).info_hash


def test_parse_torrent_rejects_data_that_is_not_a_torrent() -> None:
    with pytest.raises(ValueError):
        parse_torrent(b"this is not bencoded")
