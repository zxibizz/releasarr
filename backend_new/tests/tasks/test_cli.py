"""Tests for the operational CLI."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from src.application.queries.releases import ReleaseSummary
from src.domain.enums import ReleaseStatus
from src.tasks import cli

runner = CliRunner()


class SummaryFixture:
    def __init__(self) -> None:
        self.summary = ReleaseSummary(
            total=2,
            by_status={
                ReleaseStatus.PENDING: 1,
                ReleaseStatus.COMPLETED: 1,
            },
        )

    async def generate(self) -> ReleaseSummary:
        return self.summary


@pytest.fixture()
def summary_fixture(monkeypatch: pytest.MonkeyPatch) -> SummaryFixture:
    fixture = SummaryFixture()
    monkeypatch.setattr(cli.release_summary, "generate_summary", fixture.generate)
    return fixture


def test_release_summary_cli_json(summary_fixture: SummaryFixture) -> None:
    result = runner.invoke(cli.app, ["--json"])
    assert result.exit_code == 0
    assert '"total": 2' in result.stdout
    assert "pending" in result.stdout


def test_release_summary_cli_human(summary_fixture: SummaryFixture) -> None:
    result = runner.invoke(cli.app, [])
    assert result.exit_code == 0
    assert "Release Summary" in result.stdout
    assert "Total: 2" in result.stdout
