"""Single source of truth for reading uploaded ``.torrent`` payloads."""

from __future__ import annotations

import binascii
from base64 import b64decode
from dataclasses import dataclass

from torrentool.api import Torrent


@dataclass(slots=True, frozen=True)
class TorrentFileInfo:
    """One entry of a torrent's file list."""

    name: str
    size_bytes: int


@dataclass(slots=True, frozen=True)
class TorrentInfo:
    """Structured data extracted from torrent metadata."""

    magnet_link: str
    name: str
    files: list[TorrentFileInfo]


def decode_torrent_base64(value: str) -> bytes:
    """Decode a base64-encoded torrent payload.

    Raises:
        ValueError: if the value is empty or is not valid base64.
    """

    stripped = value.strip()
    if not stripped:
        raise ValueError("torrent_file_base64 must not be empty")

    # Browsers hand us a bare base64 payload, but a data URL is an easy mistake
    # to make and costs nothing to accept.
    if stripped.startswith("data:"):
        _, _, stripped = stripped.partition(",")

    try:
        decoded = b64decode(stripped, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("torrent_file_base64 is not valid base64") from exc

    if not decoded:
        raise ValueError("torrent_file_base64 decoded to no data")
    return decoded


def parse_torrent(data: bytes) -> TorrentInfo:
    """Parse raw torrent metadata into its magnet link, name and file list.

    Raises:
        ValueError: if the data is not a readable torrent or carries no info hash.
    """

    try:
        torrent = Torrent.from_string(data)
        magnet_link = torrent.magnet_link
    except Exception as exc:
        raise ValueError("torrent file could not be parsed") from exc

    if not magnet_link:
        raise ValueError("torrent file has no info hash")

    files = [
        TorrentFileInfo(name=file.name, size_bytes=file.length) for file in torrent.files or []
    ]
    return TorrentInfo(magnet_link=magnet_link, name=torrent.name or "", files=files)


__all__ = ["TorrentFileInfo", "TorrentInfo", "decode_torrent_base64", "parse_torrent"]
