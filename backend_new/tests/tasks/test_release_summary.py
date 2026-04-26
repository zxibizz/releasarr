"""Tests for the release summary task entrypoint."""

from __future__ import annotations

import pytest

from src.application.queries.releases.summary import ReleaseSummary
from src.domain.enums import ReleaseStatus
from src.tasks.release_summary import format_summary, generate_summary


class FakeReleaseSummaryQuery:
    def __init__(self, summary: ReleaseSummary) -> None:
        self._summary = summary

    async def fetch(self) -> ReleaseSummary:  # type: ignore[override]
        return self._summary


@pytest.mark.asyncio
async def test_generate_summary_uses_query() -> None:
    summary = ReleaseSummary(total=3, by_status={ReleaseStatus.PENDING: 3})
    query = FakeReleaseSummaryQuery(summary)

    result = await generate_summary(query)

    assert result.total == 3
    assert result.by_status[ReleaseStatus.PENDING] == 3


def test_format_summary_returns_json() -> None:
    summary = ReleaseSummary(total=1, by_status={ReleaseStatus.COMPLETED: 1})

    payload = format_summary(summary)

    assert "\"total\": 1" in payload
    assert "\"completed\": 1" in payload
