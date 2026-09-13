"""Tests for parsing Loguru's serialized log file.

The /logs endpoint is only ever as complete as this reader, so the cases that
matter are the ones where a record exists on disk but the reader could miss it:
a rotated file, or a line it cannot parse sitting between two it can.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from src.infrastructure.logs import LogFileReader


def serialized_record(
    message: str,
    *,
    level: str = "INFO",
    request_id: str | None = None,
    task: str | None = None,
    timestamp: float = 1_789_275_266.3,
    exception: dict[str, Any] | None = None,
    text: str | None = None,
) -> str:
    """Build one line in the shape Loguru's ``serialize=True`` sink writes."""

    extra: dict[str, Any] = {"request_id": request_id}
    if task is not None:
        extra["task"] = task
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


def test_parses_a_serialized_record(tmp_path: Path) -> None:
    log = tmp_path / "backend.log"
    write_log(log, serialized_record("Grabbed release", request_id="req-1", task="release_sync"))

    entries = LogFileReader(log).read_entries()

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

    levels = [entry.level for entry in LogFileReader(log).read_entries()]

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

    entry = LogFileReader(log).read_entries()[0]

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

    messages = [entry.message for entry in LogFileReader(log).read_entries()]

    assert messages == ["before", "after"]


def test_filters_combine_on_bound_fields(tmp_path: Path) -> None:
    log = tmp_path / "backend.log"
    write_log(
        log,
        serialized_record("wrong request", request_id="req-2", task="release_sync"),
        serialized_record("no task", request_id="req-1"),
        serialized_record("both", request_id="req-1", task="release_sync"),
    )

    reader = LogFileReader(log)

    assert [e.message for e in reader.read_entries(request_id="req-1")] == ["no task", "both"]
    assert [e.message for e in reader.read_entries(task="release_sync")] == [
        "wrong request",
        "both",
    ]
    assert [e.message for e in reader.read_entries(request_id="req-1", task="release_sync")] == [
        "both"
    ]


def test_reads_rotated_files_oldest_first(tmp_path: Path) -> None:
    """Rotation moves history into a sibling, which used to drop it from the API."""

    write_log(tmp_path / "backend.2026-09-01_00-00-00_000000.log", serialized_record("oldest"))
    os.utime(tmp_path / "backend.2026-09-01_00-00-00_000000.log", (1_000, 1_000))
    write_log(tmp_path / "backend.2026-09-02_00-00-00_000000.log", serialized_record("older"))
    os.utime(tmp_path / "backend.2026-09-02_00-00-00_000000.log", (2_000, 2_000))
    log = tmp_path / "backend.log"
    write_log(log, serialized_record("current"))

    entries = LogFileReader(log, history_files=3).read_entries()

    assert [entry.message for entry in entries] == ["oldest", "older", "current"]


def test_history_budget_counts_the_active_file(tmp_path: Path) -> None:
    write_log(tmp_path / "backend.2026-09-01_00-00-00_000000.log", serialized_record("oldest"))
    os.utime(tmp_path / "backend.2026-09-01_00-00-00_000000.log", (1_000, 1_000))
    write_log(tmp_path / "backend.2026-09-02_00-00-00_000000.log", serialized_record("older"))
    os.utime(tmp_path / "backend.2026-09-02_00-00-00_000000.log", (2_000, 2_000))
    log = tmp_path / "backend.log"
    write_log(log, serialized_record("current"))

    assert [e.message for e in LogFileReader(log, history_files=1).read_entries()] == ["current"]
    assert [e.message for e in LogFileReader(log, history_files=2).read_entries()] == [
        "older",
        "current",
    ]


def test_ignores_unrelated_files_in_the_log_directory(tmp_path: Path) -> None:
    write_log(tmp_path / "scheduler.log", serialized_record("another service"))
    write_log(tmp_path / "backend.log.tmp", serialized_record("not a rotation"))
    log = tmp_path / "backend.log"
    write_log(log, serialized_record("current"))

    entries = LogFileReader(log, history_files=5).read_entries()

    assert [entry.message for entry in entries] == ["current"]


def test_a_missing_log_file_yields_no_entries(tmp_path: Path) -> None:
    assert LogFileReader(tmp_path / "absent.log", history_files=3).read_entries() == []
    assert LogFileReader(tmp_path / "no" / "such" / "dir.log").read_entries() == []
