"""A download that just finished queues its import instead of waiting for the sweep.

The export task still runs on its interval; this is the fast path that keeps a
finished torrent from sitting unimported for up to five minutes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any, cast

from src.core.container import AppContainer
from src.db.session import DBManager
from src.domain.enums import SyncJobKind, SyncJobTrigger
from src.tasks.sync_steps import SyncSteps
from tests.tasks.test_sync_releases import finished_torrent, seed, torrent


class FakeClient:
    """Only what `release_sync` asks the download client for."""

    def __init__(self, torrents: list[dict[str, Any]], configured: bool = True) -> None:
        self._torrents = torrents
        self.is_configured = configured

    async def list_torrents(
        self,
        category: str | None = None,
        tag: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._torrents


@dataclass
class RecordingEnqueue:
    """Stands in for `EnqueueSyncJobUseCase`, recording what the step asked for."""

    calls: list[tuple[list[SyncJobKind], SyncJobTrigger]] = field(default_factory=list)
    error: Exception | None = None

    async def execute(
        self,
        *,
        kinds: list[SyncJobKind],
        trigger: SyncJobTrigger = SyncJobTrigger.API,
    ) -> list[Any]:
        self.calls.append((list(kinds), trigger))
        if self.error is not None:
            raise self.error
        return []


class NoOpRecompute:
    async def execute(self, request_ids: list[str], **_: object) -> None:
        return None


class NoReleases:
    async def list_request_ids_with_releases(self) -> list[str]:
        return []


def stub_container(
    db: DBManager,
    torrents: list[dict[str, Any]],
    *,
    configured: bool = True,
    enqueue: RecordingEnqueue | None = None,
) -> tuple[SyncSteps, RecordingEnqueue]:
    """A container with only the attributes `release_sync` reaches for."""

    recorder = enqueue if enqueue is not None else RecordingEnqueue()
    container = SimpleNamespace(
        db_manager=db,
        services=SimpleNamespace(qbittorrent_client=FakeClient(torrents, configured)),
        settings=SimpleNamespace(
            qbittorrent_category="releasarr",
            release_missing_grace_seconds=900,
        ),
        use_cases=SimpleNamespace(
            tasks=SimpleNamespace(enqueue_sync=recorder),
            media_requests=SimpleNamespace(recompute_state=NoOpRecompute()),
        ),
        repositories=SimpleNamespace(releases=NoReleases()),
    )
    return SyncSteps(container=cast(AppContainer, container)), recorder


async def test_a_finished_download_queues_an_export(db_manager: DBManager) -> None:
    await seed(db_manager)
    steps, enqueue = stub_container(db_manager, [finished_torrent("uploading")])

    summary = await steps.for_kind(SyncJobKind.RELEASE_SYNC)()

    assert enqueue.calls == [([SyncJobKind.EXPORT], SyncJobTrigger.DOWNLOAD_CLIENT)]
    assert summary["completed"] == 1


async def test_a_download_still_running_queues_nothing(db_manager: DBManager) -> None:
    await seed(db_manager)
    steps, enqueue = stub_container(db_manager, [torrent("downloading")])

    summary = await steps.for_kind(SyncJobKind.RELEASE_SYNC)()

    assert enqueue.calls == []
    assert summary["completed"] == 0


async def test_an_unconfigured_client_queues_nothing(db_manager: DBManager) -> None:
    await seed(db_manager)
    steps, enqueue = stub_container(db_manager, [], configured=False)

    summary = await steps.for_kind(SyncJobKind.RELEASE_SYNC)()

    assert enqueue.calls == []
    assert summary["skipped"] is True


async def test_a_failed_queue_write_still_finishes_the_step(db_manager: DBManager) -> None:
    """The release is finished either way, and the periodic export is the fallback."""

    await seed(db_manager)
    enqueue = RecordingEnqueue(error=RuntimeError("jobs table is gone"))
    steps, _ = stub_container(db_manager, [finished_torrent("uploading")], enqueue=enqueue)

    summary = await steps.for_kind(SyncJobKind.RELEASE_SYNC)()

    assert summary["completed"] == 1
