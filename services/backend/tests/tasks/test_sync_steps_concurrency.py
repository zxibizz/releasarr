"""The periodic loops and the queued-job runner share one ``SyncSteps``.

Both can reach the same task at once, and a slow step - an export waiting on
Sonarr to finish copying - leaves a window wide enough for them to duplicate
each other's work against the same releases.
"""

from __future__ import annotations

import asyncio
from typing import cast

import pytest

from src.core.container import AppContainer
from src.domain.enums import SyncJobKind
from src.tasks.sync_steps import StepSummary, SyncSteps


class TrackingSteps(SyncSteps):
    """Steps recording how many runs of each kind were in flight at once."""

    def __init__(self) -> None:
        super().__init__(container=cast(AppContainer, None))
        self.active: dict[str, int] = {}
        self.peak: dict[str, int] = {}
        self.order: list[str] = []

    async def _track(self, name: str) -> StepSummary:
        self.active[name] = self.active.get(name, 0) + 1
        self.peak[name] = max(self.peak.get(name, 0), self.active[name])
        self.order.append(name)
        await asyncio.sleep(0.02)
        self.active[name] -= 1
        return {}

    async def export(self) -> StepSummary:
        return await self._track("export")

    async def regrab(self) -> StepSummary:
        return await self._track("regrab")


@pytest.fixture()
def steps() -> TrackingSteps:
    return TrackingSteps()


async def test_one_task_cannot_run_twice_at_once(steps: TrackingSteps) -> None:
    run = steps.for_kind(SyncJobKind.EXPORT)

    await asyncio.gather(run(), run())

    assert steps.peak["export"] == 1
    assert steps.order == ["export", "export"]


async def test_a_queued_run_still_happens_rather_than_being_dropped(
    steps: TrackingSteps,
) -> None:
    """A manual trigger has to run, even if it only finds the work already done."""

    await asyncio.gather(*(steps.for_kind(SyncJobKind.EXPORT)() for _ in range(3)))

    assert steps.order == ["export"] * 3


async def test_different_tasks_are_not_blocked_by_each_other(steps: TrackingSteps) -> None:
    await asyncio.gather(
        steps.for_kind(SyncJobKind.EXPORT)(),
        steps.for_kind(SyncJobKind.REGRAB)(),
    )

    assert steps.peak == {"export": 1, "regrab": 1}
    assert sorted(steps.order) == ["export", "regrab"]
