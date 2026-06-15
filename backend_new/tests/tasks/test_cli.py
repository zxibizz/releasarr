"""Tests for the operational CLI."""

from __future__ import annotations

import pytest
from types import SimpleNamespace

from typer.testing import CliRunner

from src.application.queries.releases import ReleaseSummary
from src.domain.enums import ReleaseStatus
from src.application.use_cases.requests.sync_sonarr import SyncSonarrResult
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
    result = runner.invoke(cli.app, ["release-summary", "--json"])
    assert result.exit_code == 0
    assert '"total": 2' in result.stdout
    assert "pending" in result.stdout


def test_release_summary_cli_human(summary_fixture: SummaryFixture) -> None:
    result = runner.invoke(cli.app, ["release-summary"])
    assert result.exit_code == 0
    assert "Release Summary" in result.stdout
    assert "Total: 2" in result.stdout


class FakeSyncUseCase:
    def __init__(self) -> None:
        self.calls = 0

    async def execute(self) -> SyncSonarrResult:
        self.calls += 1
        return SyncSonarrResult(created=1, updated=2, completed=3)


class FakeContainer:
    def __init__(self, use_case: FakeSyncUseCase) -> None:
        self.started = False
        self.stopped = False
        self.use_cases = SimpleNamespace(
            media_requests=SimpleNamespace(sync_sonarr=use_case)
        )

    def startup(self) -> None:
        self.started = True

    def shutdown(self) -> None:
        self.stopped = True


def test_sync_sonarr_requests_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    use_case = FakeSyncUseCase()
    container = FakeContainer(use_case)
    monkeypatch.setattr(cli, "get_container", lambda: container)

    result = runner.invoke(cli.app, ["sync-sonarr-requests"])

    assert result.exit_code == 0
    assert "created=1" in result.stdout
    assert "updated=2" in result.stdout
    assert "completed=3" in result.stdout
    assert container.started is True
    assert container.stopped is True
    assert use_case.calls == 1
