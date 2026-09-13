"""Page bounds shared by the indexer listings that Prowlarr paginates."""

from __future__ import annotations

from src.settings.config import AppSettings


def normalise_page(page: int | None, settings: AppSettings) -> int:
    if page is None or page <= 0:
        return settings.default_page
    return page


def normalise_per_page(per_page: int | None, settings: AppSettings) -> int:
    """Cap the page size before it reaches Prowlarr.

    Prowlarr would happily serve thousands of rows in one response, and both of
    these lists run to tens of thousands on a busy instance.
    """

    if per_page is None or per_page <= 0:
        per_page = settings.default_page_size
    return min(per_page, settings.max_page_size)


__all__ = ["normalise_page", "normalise_per_page"]
