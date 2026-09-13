"""Custom exceptions for the indexer endpoints."""

from __future__ import annotations


class ProwlarrNotConfiguredError(RuntimeError):
    """Raised when indexers are asked for without Prowlarr being set up.

    Release search silently degrades to finding nothing when Prowlarr is
    missing, but this page exists to answer "are my indexers working", and an
    empty list is the wrong answer to that: it reads as "no indexers" rather
    than "no Prowlarr".
    """

    def __init__(self) -> None:
        super().__init__(
            "Prowlarr is not configured; set RELEASARR_PROWLARR_URL and "
            "RELEASARR_PROWLARR_API_KEY to inspect indexers"
        )


__all__ = ["ProwlarrNotConfiguredError"]
