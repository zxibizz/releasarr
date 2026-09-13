"""Tests for parsing the processes' serialized log files.

The /logs endpoint is only ever as complete as this reader, so the cases that
matter are the ones where a record exists on disk but the reader could miss it: a
rotated file, a line it cannot parse sitting between two it can, or a record in
the other process's file.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from src.domain.enums import LogService
from src.infrastructure.logs import LogFileReader


def serialized_record(
    message: str,
    *,
    level: str = "INFO",
    request_id: str | None = None,
    task: str | None = None,
    service: str | None = None,
    timestamp: float = 1_789_275_266.3,
    exception: dict[str, Any] | None = None,
    text: str | None = None,
) -> str:
    """Build one line in the shape Loguru's ``serialize=True`` sink writes."""

    extra: dict[str, Any] = {"request_id": request_id}
    if task is not None:
        extra["task"] = task
    if service is not None:
        extra["service"] = service
    payload = {
        "text": text or f"2026-09-13 04:54:26.300 | {level} | mod:fn:1 - {message}\n",
        "record": {
            "time": {"repr": "2026-09-13 04:54:26.300466+00:00", "timestamp": timestamp},
            "level": {"name": level, "no": 20},
            "message": message,
            "extra": extra,
            "name": "src.tasks.sync_releases",
            "module": "sync_releases",
            "exception": exception,
        },
    }
    return json.dumps(payload)


def write_log(path: Path, *lines: str, mtime: int | None = None) -> None:
    path.write_text("".join(f"{line}\n" for line in lines), encoding="utf-8")
    if mtime is not None:
        os.utime(path, (mtime, mtime))


def make_reader(
    log: Path, *, service: str = LogService.API.value, history_files: int = 1
) -> LogFileReader:
    """Read one file.

    The API's file is the default, because it is also the one holding records
    written before the processes had files of their own.
    """

    return LogFileReader({service: log}, history_files=history_files)


def test_parses_a_serialized_record(tmp_path: Path) -> None:
    log = tmp_path / "backend.log"
    write_log(log, serialized_record("Grabbed release", request_id="req-1", task="release_sync"))
    entries = make_reader(log).read_entries()

    assert len(entries) == 1
    entry = entries[0]
    assert entry.message == "Grabbed release"
    assert entry.level == "info"
    assert entry.occurred_at == 1_789_275_266_300
    assert entry.source == "src.tasks.sync_releases"
    assert entry.metadata is not None
    assert entry.metadata["request_id"] == "req-1"
    assert entry.stack_trace is None


def test_maps_loguru_levels_onto_the_three_exposed_levels(tmp_path: Path) -> None:
    log = tmp_path / "backend.log"
    write_log(
        log,
        serialized_record("trace", level="TRACE"),
        serialized_record("debug", level="DEBUG"),
        serialized_record("success", level="SUCCESS"),
        serialized_record("warned", level="WARNING"),
        serialized_record("failed", level="ERROR"),
        serialized_record("died", level="CRITICAL"),
        serialized_record("odd", level="NOTALEVEL"),
    )

    levels = [entry.level for entry in make_reader(log).read_entries()]

    assert levels == ["info", "info", "info", "warning", "error", "error", "info"]


def test_exposes_the_traceback_of_a_failure(tmp_path: Path) -> None:
    log = tmp_path / "backend.log"
    write_log(
        log,
        serialized_record(
            "Failed to export release",
            level="ERROR",
            exception={"type": "ValueError", "value": "boom", "traceback": True},
            text="2026-09-13 04:54:26.300 | ERROR | mod:fn:1 - boom\nTraceback:\n  ValueError\n",
        ),
    )

    entry = make_reader(log).read_entries()[0]

    assert entry.stack_trace is not None
    assert "Traceback" in entry.stack_trace


def test_skips_lines_it_cannot_parse(tmp_path: Path) -> None:
    """A truncated line, as a crash mid-write leaves behind, must not hide the rest."""

    log = tmp_path / "backend.log"
    write_log(
        log,
        serialized_record("before"),
        '{"record": {"time"',
        "",
        "not json at all",
        json.dumps({"no_record_key": True}),
        serialized_record("after"),
    )

    messages = [entry.message for entry in make_reader(log).read_entries()]

    assert messages == ["before", "after"]


def test_filters_combine_on_bound_fields(tmp_path: Path) -> None:
    log = tmp_path / "backend.log"
    write_log(
        log,
        serialized_record("wrong request", request_id="req-2", task="release_sync"),
        serialized_record("no task", request_id="req-1"),
        serialized_record("both", request_id="req-1", task="release_sync"),
    )

    reader = make_reader(log)

    assert [e.message for e in reader.read_entries(request_id="req-1")] == ["no task", "both"]
    assert [e.message for e in reader.read_entries(task="release_sync")] == [
        "wrong request",
        "both",
    ]
    assert [e.message for e in reader.read_entries(request_id="req-1", task="release_sync")] == [
        "both"
    ]


def test_filters_by_the_process_that_wrote_the_record(tmp_path: Path) -> None:
    log = tmp_path / "backend.log"
    write_log(
        log,
        serialized_record("served a request", service="api"),
        serialized_record("ran a task", service="scheduler"),
        serialized_record("also the api", service="API"),
    )

    reader = make_reader(log)

    assert [e.message for e in reader.read_entries(service="api")] == [
        "served a request",
        "also the api",
    ]
    assert [e.message for e in reader.read_entries(service="scheduler")] == ["ran a task"]


def test_min_level_returns_that_severity_and_worse(tmp_path: Path) -> None:
    """A threshold, not an exact match: someone chasing a problem wants the lot."""

    log = tmp_path / "backend.log"
    write_log(
        log,
        serialized_record("routine", level="INFO"),
        serialized_record("quiet detail", level="DEBUG"),
        serialized_record("worth a look", level="WARNING"),
        serialized_record("broken", level="ERROR"),
        serialized_record("also broken", level="CRITICAL"),
    )

    reader = make_reader(log)

    assert [e.message for e in reader.read_entries(min_level="warning")] == [
        "worth a look",
        "broken",
        "also broken",
    ]
    assert [e.message for e in reader.read_entries(min_level="error")] == [
        "broken",
        "also broken",
    ]
    # Debug is folded into info, so a floor of info is a floor of everything.
    assert len(reader.read_entries(min_level="info")) == 5
    assert len(reader.read_entries()) == 5


def test_min_level_combines_with_the_other_filters(tmp_path: Path) -> None:
    log = tmp_path / "backend.log"
    write_log(
        log,
        serialized_record("api failure", level="ERROR", service="api"),
        serialized_record("scheduler noise", level="INFO", service="scheduler"),
        serialized_record("scheduler failure", level="ERROR", service="scheduler"),
    )

    reader = make_reader(log)

    assert [e.message for e in reader.read_entries(service="scheduler", min_level="warning")] == [
        "scheduler failure"
    ]


def test_merges_both_files_in_time_order(tmp_path: Path) -> None:
    """A request's activity spans both processes, so neither file alone is the answer."""

    api = tmp_path / "backend.log"
    scheduler = tmp_path / "scheduler.log"
    write_log(
        api,
        serialized_record("accepted the request", timestamp=1_000.0),
        serialized_record("reported back", timestamp=3_000.0),
    )
    write_log(scheduler, serialized_record("ran the task", timestamp=2_000.0))

    reader = LogFileReader({"api": api, "scheduler": scheduler})

    assert [entry.message for entry in reader.read_entries()] == [
        "accepted the request",
        "ran the task",
        "reported back",
    ]


def test_each_sources_records_answer_for_their_own_service(tmp_path: Path) -> None:
    api = tmp_path / "backend.log"
    scheduler = tmp_path / "scheduler.log"
    write_log(api, serialized_record("handled a request"))
    write_log(scheduler, serialized_record("starting scheduler service"))

    reader = LogFileReader({"api": api, "scheduler": scheduler})

    assert [e.message for e in reader.read_entries(service="api")] == ["handled a request"]
    assert [e.message for e in reader.read_entries(service="scheduler")] == [
        "starting scheduler service"
    ]
    assert len(reader.read_entries()) == 2


def test_a_records_own_tag_beats_the_file_it_sits_in(tmp_path: Path) -> None:
    """The API's file holds the scheduler's records from before they were split."""

    log = tmp_path / "backend.log"
    write_log(
        log,
        serialized_record("tagged by the scheduler", service="Scheduler"),
        serialized_record("handled a request"),
    )

    reader = make_reader(log)

    assert [e.message for e in reader.read_entries(service="scheduler")] == [
        "tagged by the scheduler"
    ]
    assert [e.message for e in reader.read_entries(service="api")] == ["handled a request"]


def test_records_written_before_processes_were_tagged_still_resolve(tmp_path: Path) -> None:
    """Older records carry no service, and dropping them would empty the view."""

    log = tmp_path / "backend.log"
    write_log(
        log,
        serialized_record("legacy task line", task="release_sync"),
        serialized_record("legacy request line", request_id="req-1"),
        serialized_record("no metadata at all"),
    )

    reader = make_reader(log)

    assert [e.message for e in reader.read_entries(service="scheduler")] == ["legacy task line"]
    assert [e.message for e in reader.read_entries(service="api")] == [
        "legacy request line",
        "no metadata at all",
    ]


def test_reads_rotated_files_oldest_first(tmp_path: Path) -> None:
    """Rotation moves history into a sibling, which used to drop it from the API."""

    write_log(tmp_path / "backend.2026-09-01_00-00-00_000000.log", serialized_record("oldest"))
    os.utime(tmp_path / "backend.2026-09-01_00-00-00_000000.log", (1_000, 1_000))
    write_log(tmp_path / "backend.2026-09-02_00-00-00_000000.log", serialized_record("older"))
    os.utime(tmp_path / "backend.2026-09-02_00-00-00_000000.log", (2_000, 2_000))
    log = tmp_path / "backend.log"
    write_log(log, serialized_record("current"))

    entries = make_reader(log, history_files=3).read_entries()

    assert [entry.message for entry in entries] == ["oldest", "older", "current"]


def test_history_budget_counts_the_active_file(tmp_path: Path) -> None:
    write_log(tmp_path / "backend.2026-09-01_00-00-00_000000.log", serialized_record("oldest"))
    os.utime(tmp_path / "backend.2026-09-01_00-00-00_000000.log", (1_000, 1_000))
    write_log(tmp_path / "backend.2026-09-02_00-00-00_000000.log", serialized_record("older"))
    os.utime(tmp_path / "backend.2026-09-02_00-00-00_000000.log", (2_000, 2_000))
    log = tmp_path / "backend.log"
    write_log(log, serialized_record("current"))

    assert [e.message for e in make_reader(log, history_files=1).read_entries()] == ["current"]
    assert [e.message for e in make_reader(log, history_files=2).read_entries()] == [
        "older",
        "current",
    ]


def test_history_budget_applies_to_each_file_on_its_own(tmp_path: Path) -> None:
    write_log(
        tmp_path / "backend.2026-09-01_00-00-00_000000.log",
        serialized_record("api history", timestamp=1_000.0),
    )
    os.utime(tmp_path / "backend.2026-09-01_00-00-00_000000.log", (1_000, 1_000))
    write_log(
        tmp_path / "scheduler.2026-09-01_00-00-00_000000.log",
        serialized_record("scheduler history", timestamp=1_000.0),
    )
    os.utime(tmp_path / "scheduler.2026-09-01_00-00-00_000000.log", (1_000, 1_000))
    write_log(tmp_path / "backend.log", serialized_record("api now", timestamp=2_000.0))
    write_log(tmp_path / "scheduler.log", serialized_record("scheduler now", timestamp=2_000.0))

    reader = LogFileReader(
        {"api": tmp_path / "backend.log", "scheduler": tmp_path / "scheduler.log"},
        history_files=2,
    )

    # Both files' rotations, then both active files; ties keep source order.
    assert [entry.message for entry in reader.read_entries()] == [
        "api history",
        "scheduler history",
        "api now",
        "scheduler now",
    ]


def test_ignores_files_it_was_not_pointed_at(tmp_path: Path) -> None:
    """Only the sources handed in are read; a stray file in the directory is not one."""

    write_log(tmp_path / "scheduler.log", serialized_record("another process"))
    write_log(tmp_path / "backend.log.tmp", serialized_record("not a rotation"))
    log = tmp_path / "backend.log"
    write_log(log, serialized_record("current"))

    entries = make_reader(log, history_files=5).read_entries()

    assert [entry.message for entry in entries] == ["current"]


def test_a_missing_log_file_yields_no_entries(tmp_path: Path) -> None:
    assert make_reader(tmp_path / "absent.log", history_files=3).read_entries() == []
    assert make_reader(tmp_path / "no" / "such" / "dir.log").read_entries() == []


def test_a_missing_source_leaves_the_others_readable(tmp_path: Path) -> None:
    """A fresh install has no scheduler file until the worker first starts."""

    api = tmp_path / "backend.log"
    write_log(api, serialized_record("handled a request"))

    reader = LogFileReader(
        {"api": api, "scheduler": tmp_path / "scheduler.log"},
    )

    assert [e.message for e in reader.read_entries()] == ["handled a request"]
