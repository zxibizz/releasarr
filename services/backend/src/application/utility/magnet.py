"""Single source of truth for parsing magnet URIs."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qs, unquote, urlparse


@dataclass(slots=True, frozen=True)
class MagnetInfo:
    """Structured data extracted from a magnet link."""

    info_hash: str
    display_name: str


def parse_magnet(magnet_link: str) -> MagnetInfo:
    """Parse a magnet URI into its info hash and display name.

    Raises:
        ValueError: if the link is not a magnet URI or has no info hash.
    """

    parsed = urlparse(magnet_link)
    if parsed.scheme != "magnet":
        raise ValueError("magnet_link must be a magnet URI")

    params = parse_qs(parsed.query)
    info_hash: str | None = None
    for value in params.get("xt", []):
        if value.startswith("urn:btih:"):
            info_hash = value.split(":")[-1].upper()
            break
    if info_hash is None:
        raise ValueError("magnet_link missing info hash")

    dn_values = params.get("dn", [])
    display_name = unquote(dn_values[0]) if dn_values else ""
    if not display_name:
        display_name = info_hash

    return MagnetInfo(info_hash=info_hash, display_name=display_name)


__all__ = ["MagnetInfo", "parse_magnet"]
