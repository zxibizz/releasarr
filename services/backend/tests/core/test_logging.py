"""Tests for the Loguru configuration behind the log file.

The log file is both a diagnostic tool and the source of every request's activity
view, and it is served to the browser. That combination is what these tests guard:
nothing secret may reach it, and nothing user-facing may be filtered out of it.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any, TypedDict

import pytest
from loguru import logger

from src.core.logging import InterceptHandler, configure_logging, redact_secrets
from src.domain.enums import LogService
from src.settings.config import AppSettings


@pytest.fixture(autouse=True)
def restore_logging() -> Iterator[None]:
    """Leave global Loguru and stdlib state as the rest of the suite expects it.

    ``configure`` treats a ``None`` patcher as "leave it alone", so clearing the
    redaction patcher means installing one that does nothing.
    """

    try:
        yield
    finally:
        logger.remove()
        logger.configure(extra={}, patcher=lambda record: None)
        logging.getLogger("httpx").setLevel(logging.NOTSET)
        # configure_logging also puts an InterceptHandler on the root logger. Left
        # there, every library's records keep being funnelled into Loguru for the
        # rest of the suite and land in other tests' sinks. Only ours is dropped;
        # what pytest installed for its own capture stays.
        root = logging.getLogger()
        root.handlers = [
            handler for handler in root.handlers if not isinstance(handler, InterceptHandler)
        ]


def written_records(log_file: Path) -> list[dict[str, Any]]:
    logger.complete()
    if not log_file.exists():
        return []
    return [
        json.loads(line)["record"]
        for line in log_file.read_text(encoding="utf-8").splitlines()
        if line
    ]


def configure(tmp_path: Path, **overrides: Any) -> Path:
    """Configure the API's sinks against temporary files and return its file."""

    configure_logging(AppSettings(**log_files(tmp_path), **overrides), service=LogService.API)
    return tmp_path / "backend.log"


class LogFiles(TypedDict):
    """The two sinks `configure` points at temporary files, named as fields are."""

    log_file: str
    scheduler_log_file: str


def log_files(tmp_path: Path) -> LogFiles:
    return {
        "log_file": str(tmp_path / "backend.log"),
        "scheduler_log_file": str(tmp_path / "scheduler.log"),
    }


def test_redacts_credentials_from_a_query_string() -> None:
    record = {"message": "GET https://api.themoviedb.org/3/movie/1?api_key=SECRET&language=en"}

    redact_secrets(record)  # type: ignore[arg-type]

    assert record["message"] == ("GET https://api.themoviedb.org/3/movie/1?api_key=***&language=en")


@pytest.mark.parametrize(
    "message",
    [
        "?apikey=SECRET",
        "?API_KEY=SECRET",
        "?token=SECRET",
        "?password=SECRET",
        "?api_key=SECRET&next=1",
        '"?api_key=SECRET"',
    ],
)
def test_redacts_every_credential_spelling(message: str) -> None:
    record = {"message": message}

    redact_secrets(record)  # type: ignore[arg-type]

    assert "SECRET" not in record["message"]


def test_the_log_file_never_receives_a_credential(tmp_path: Path) -> None:
    """A leaked key would be readable through /logs, not just on disk."""
    log_file = configure(tmp_path)

    logger.info("Calling https://api.themoviedb.org/3/movie/1?api_key=SUPERSECRET")
    logger.complete()

    contents = log_file.read_text(encoding="utf-8")
    assert "SUPERSECRET" not in contents
    assert "api_key=***" in contents


def test_transport_chatter_is_muted(tmp_path: Path) -> None:
    """httpx logs whole request URLs at INFO, which is where keys used to leak."""

    log_file = configure(tmp_path)

    logging.getLogger("httpx").info("HTTP Request: GET https://host/x?api_key=SUPERSECRET")
    logging.getLogger("httpx").warning("something actually went wrong")

    messages = [record["message"] for record in written_records(log_file)]
    assert messages == ["something actually went wrong"]


def test_the_log_file_keeps_recording_info_when_the_console_is_quiet(tmp_path: Path) -> None:
    """Raising the console threshold must not blank out request activity."""

    log_file = configure(tmp_path, log_level="WARNING")

    logger.info("Grabbed release", request_id="req-1")

    records = written_records(log_file)
    assert [record["message"] for record in records] == ["Grabbed release"]
    assert records[0]["extra"]["request_id"] == "req-1"


def test_a_verbose_setting_still_reaches_the_log_file(tmp_path: Path) -> None:
    log_file = configure(tmp_path, log_level="DEBUG")

    logger.debug("Updated media request", request_id="req-1")

    assert [record["message"] for record in written_records(log_file)] == ["Updated media request"]


def test_an_unknown_level_falls_back_instead_of_failing(tmp_path: Path) -> None:
    log_file = configure(tmp_path, log_level="NONSENSE")

    logger.info("still recorded")

    assert [record["message"] for record in written_records(log_file)] == ["still recorded"]


def test_records_name_the_process_that_wrote_them(tmp_path: Path) -> None:
    """Both processes write to one file, so the /logs view splits them by this."""

    log_file = configure(tmp_path)

    logger.info("Served request")

    assert written_records(log_file)[0]["extra"]["service"] == "api"


def test_each_process_writes_its_own_file(tmp_path: Path) -> None:
    """Sharing one file let either process rotate the other's history away."""

    configure_logging(AppSettings(**log_files(tmp_path)), service=LogService.SCHEDULER)

    logger.info("Running task")
    logger.complete()

    assert [record["message"] for record in written_records(tmp_path / "scheduler.log")] == [
        "Running task"
    ]
    assert not (tmp_path / "backend.log").exists()


def test_intercepted_records_are_attributed_to_their_caller(tmp_path: Path) -> None:
    """Without a frame depth every library log claims to come from our handler."""

    log_file = configure(tmp_path)

    logging.getLogger("alembic").warning("migrating")

    record = written_records(log_file)[0]
    assert record["name"] != "src.core.logging"
    # The old handler leaked its own bookkeeping into the UI's metadata line.
    assert "logger_name" not in record["extra"]


def test_every_module_binds_a_component() -> None:
    """A module logging through bare loguru has no component, so the logs view
    could neither group it nor filter it. ``get_logger`` requires one, so the
    only way to log without one is to import loguru's logger directly - which
    is what this test forbids outside the one module that wraps it.

    The task modules in the allowlist keep the import for `logger.__class__`
    typing or `logger.contextualize()`, not for emitting records; the class
    they run is bound separately.
    """

    import ast

    src_root = Path(__file__).resolve().parents[2] / "src"
    allowlist = {
        "core/logging.py",
        "tasks/scheduler_service.py",
        "tasks/sync_jobs.py",
        "tasks/sync_releases.py",
        "tasks/sync_steps.py",
    }
    offenders: list[str] = []
    for path in sorted(src_root.rglob("*.py")):
        rel = str(path.relative_to(src_root))
        if rel in allowlist:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ImportFrom)
                and node.module == "loguru"
                and any(alias.name == "logger" for alias in node.names)
            ):
                offenders.append(rel)

    assert offenders == []
