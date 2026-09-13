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
from typing import Any

import pytest
from loguru import logger

from src.core.logging import configure_logging, redact_secrets
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
    log_file = tmp_path / "backend.log"
    configure_logging(AppSettings(log_file=str(log_file), **overrides))
    return log_file


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


def test_intercepted_records_are_attributed_to_their_caller(tmp_path: Path) -> None:
    """Without a frame depth every library log claims to come from our handler."""

    log_file = configure(tmp_path)

    logging.getLogger("alembic").warning("migrating")

    record = written_records(log_file)[0]
    assert record["name"] != "src.core.logging"
    # The old handler leaked its own bookkeeping into the UI's metadata line.
    assert "logger_name" not in record["extra"]
