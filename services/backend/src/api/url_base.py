"""Print the effective URL base, for the container's nginx site.

The image's init runs this after migrations and renders the site from what it
prints, so a URL base saved in Settings takes effect on the next restart, as the
*arr apps' own does. An unreadable database falls back to the environment's
value rather than holding the container's boot on it.
"""

from __future__ import annotations

import asyncio
import sys

from src.core.container import get_container
from src.db.session import get_async_engine


async def resolve_url_base() -> str:
    container = get_container()
    try:
        await container.settings_provider.reload_now()
    except Exception as exc:
        print(f"url base: using the environment, settings unreadable: {exc}", file=sys.stderr)
    finally:
        await get_async_engine().dispose()
    return container.settings.url_base


__all__ = ["resolve_url_base"]


if __name__ == "__main__":
    print(asyncio.run(resolve_url_base()))
