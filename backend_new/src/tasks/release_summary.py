"""Task entrypoint for printing aggregated release summaries."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from src.application.queries.releases import ReleaseSummary, ReleaseSummaryQuery
from src.core.container import get_container


async def generate_summary(query: ReleaseSummaryQuery | None = None) -> ReleaseSummary:
    """Fetch release summary statistics using the shared container query."""

    if query is None:
        container = get_container()
        query = container.release_summary_query
    return await query.fetch()


def format_summary(summary: ReleaseSummary) -> str:
    """Format a release summary into a human-friendly JSON string."""

    payload: dict[str, Any] = {
        "total": summary.total,
        "by_status": {status.value: count for status, count in summary.by_status.items()},
    }
    return json.dumps(payload, indent=2, sort_keys=True)


async def main() -> None:
    """Entry point executed by the task runner."""

    summary = await generate_summary()
    print(format_summary(summary))


if __name__ == "__main__":
    asyncio.run(main())
