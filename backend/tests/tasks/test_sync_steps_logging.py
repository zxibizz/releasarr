"""The logs view filters on a `task` field bound while a task runs.

The tag has to reach log calls made several layers below the step itself,
otherwise filtering by task would only ever return the runner's own lines.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from typing import Any, cast

import pytest
from loguru import logger

from src.core.container import AppContainer
from src.domain.enums import SyncJobKind
from src.tasks.sync_steps import StepSummary, SyncSteps


class RecordingSteps(SyncSteps):
    """Steps that only log, so the tag is all that is under test."""

    async def sonarr_sync(self) -> StepSummary:
        self._started.set()
        await asyncio.sleep(0.05)
        logger.info("sonarr_sync done")
        return {}

    async def release_sync(self) -> StepSummary:
        await self._started.wait()
        logger.info("release_sync done")
        return {}

    async def export(self) -> StepSummary:
        # Stands in for a use case logging well below the step boundary.
        logger.bind(component="export_finished_series").info("Imported a release")
        return {}

    async def regrab(self) -> StepSummary:
        return {}

    _started = asyncio.Event()


@pytest.fixture()
def captured() -> Iterator[list[dict[str, Any]]]:
    """Collect the message and bound context of every record logged in a test."""

    records: list[dict[str, Any]] = []

    def sink(message: Any) -> None:
        records.append(
            {"message": message.record["message"], **dict(message.record["extra"])},
        )

    sink_id = logger.add(sink, level=0)
    try:
        yield records
    finally:
        logger.remove(sink_id)


@pytest.fixture()
def steps() -> RecordingSteps:
    instance = RecordingSteps(container=cast(AppContainer, None))
    RecordingSteps._started = asyncio.Event()
    return instance


def find(records: list[dict[str, Any]], message: str) -> dict[str, Any] | None:
    return next((record for record in records if record["message"] == message), None)


async def test_task_tag_reaches_nested_log_calls(
    steps: RecordingSteps,
    captured: list[dict[str, Any]],
) -> None:
    await steps.for_kind(SyncJobKind.EXPORT)()

    record = find(captured, "Imported a release")
    assert record is not None
    assert record["task"] == "export"
    assert record["component"] == "export_finished_series"


async def test_the_tag_does_not_outlive_the_task(
    steps: RecordingSteps,
    captured: list[dict[str, Any]],
) -> None:
    await steps.for_kind(SyncJobKind.REGRAB)()

    logger.info("Unrelated line")

    record = find(captured, "Unrelated line")
    assert record is not None
    assert record.get("task") is None


async def test_concurrent_tasks_keep_their_own_tag(
    steps: RecordingSteps,
    captured: list[dict[str, Any]],
) -> None:
    """Task loops run side by side, so a shared tag would mislabel their logs."""

    await asyncio.gather(
        steps.for_kind(SyncJobKind.SONARR_SYNC)(),
        steps.for_kind(SyncJobKind.RELEASE_SYNC)(),
    )

    slow = find(captured, "sonarr_sync done")
    quick = find(captured, "release_sync done")
    assert slow is not None and quick is not None
    assert slow["task"] == "sonarr_sync"
    assert quick["task"] == "release_sync"
