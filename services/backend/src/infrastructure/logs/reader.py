"""Reader for the structured (Loguru JSON) log files backing the /logs endpoint."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.domain.enums import LogService

_LEVEL_MAP = {
    "TRACE": "info",
    "DEBUG": "info",
    "INFO": "info",
    "SUCCESS": "info",
    "WARNING": "warning",
    "ERROR": "error",
    "CRITICAL": "error",
}

# Loguru's seven levels collapse onto three, so severity has to be stated here
# rather than read back off the names. The filter below is a threshold: warning
# means warning and worse, which is what someone chasing a problem asks for.
_LEVEL_SEVERITY = {"info": 0, "warning": 1, "error": 2}


@dataclass(slots=True)
class LogEntry:
    """A single structured log record exposed to the application layer."""

    id: str
    occurred_at: int
    timestamp: str
    level: str
    message: str
    component: str | None = None
    source: str | None = None
    metadata: dict[str, Any] | None = field(default=None)
    stack_trace: str | None = None


class LogFileReader:
    """Parse the processes' serialized JSON log files into :class:`LogEntry` records.

    Each process owns a file, and a record's own ``service`` — or, for records old
    enough to predate that tag, the file it sits in — says which process wrote it.
    Both files are read and merged in time order, because a request's activity
    spans them: the API logs accepting the request, and the scheduler logs the work
    that request went on to queue.
    """

    def __init__(self, sources: Mapping[str, str | Path], history_files: int = 1) -> None:
        # Keyed by the service that writes each file, and ordered, so records that
        # share a timestamp keep a stable order between files.
        self._sources = {name: Path(path) for name, path in sources.items()}
        # Reading every surviving rotation would make each call scale with the
        # retention window, so only the most recent few of each file are in reach.
        self._history_files = max(1, history_files)

    def read_entries(
        self,
        request_id: str | None = None,
        task: str | None = None,
        service: str | None = None,
        component: str | None = None,
        min_level: str | None = None,
    ) -> list[LogEntry]:
        """Return log entries in chronological order, optionally filtered.

        Filters are combined. The first four match on fields the producer bound
        onto the record rather than on the message text; ``min_level`` is the odd
        one out, matching on severity once the record has been parsed.
        """

        entries: list[LogEntry] = []
        for source, base in self._sources.items():
            for path in self._log_files(base):
                with path.open("r", encoding="utf-8") as handle:
                    for line in handle:
                        stripped = line.strip()
                        if not stripped:
                            continue
                        entry = self._parse_line(stripped)
                        if entry is None:
                            continue
                        if request_id is not None and not self._matches(
                            entry, "request_id", request_id
                        ):
                            continue
                        if task is not None and not self._matches(entry, "task", task):
                            continue
                        if (
                            service is not None
                            and self._service_of(entry, source) != service.lower()
                        ):
                            continue
                        if component is not None and entry.component != component:
                            continue
                        if min_level is not None and not self._at_least(entry, min_level):
                            continue
                        entries.append(entry)

        # Each file is written in order, but the two processes interleave in time,
        # so the merged list has to be sorted. Python's sort is stable, which
        # leaves records that share a timestamp in the order they were read.
        entries.sort(key=lambda entry: entry.occurred_at)
        return entries

    @staticmethod
    def _at_least(entry: LogEntry, min_level: str) -> bool:
        return _LEVEL_SEVERITY.get(entry.level, 0) >= _LEVEL_SEVERITY.get(min_level.lower(), 0)

    @staticmethod
    def _service_of(entry: LogEntry, source: str) -> str:
        """Return the process that wrote a record, as ``LogService`` spells it.

        A record names its own process. Records written before the processes
        tagged themselves do not, and there the file is the next best answer —
        except in the file the API has kept since before the split, which also
        holds the scheduler's older records. Work done inside a background task
        always has ``task`` bound onto it by ``SyncSteps.for_kind``, and the API
        never runs one, so that field is what separates the rest.
        """

        metadata = entry.metadata
        if metadata is not None:
            raw = metadata.get("service")
            if raw is not None:
                return str(raw).lower()
            if "task" in metadata:
                return LogService.SCHEDULER.value
        return source

    def _log_files(self, base: Path) -> list[Path]:
        """Return one process's files to scan, oldest first.

        Rotation moves history out of the configured path into a timestamped
        sibling (``backend.log`` becomes ``backend.2026-09-13_04-54-26_300466.log``),
        so reading only the active file would drop everything logged before the
        last rotation.
        """
        rotated = [
            path
            for path in base.parent.glob(f"{base.stem}.*{base.suffix}")
            if path != base and path.is_file()
        ]
        rotated.sort(key=lambda path: (path.stat().st_mtime, path.name))

        # The active file counts against the budget and is always the newest.
        keep = self._history_files - 1
        recent = rotated[-keep:] if keep > 0 else []
        return [path for path in [*recent, base] if path.exists()]

    @staticmethod
    def _matches(entry: LogEntry, key: str, value: str) -> bool:
        metadata = entry.metadata
        return metadata is not None and metadata.get(key) == value

    def _parse_line(self, line: str) -> LogEntry | None:
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            return None

        record = payload.get("record")
        if not isinstance(record, dict):
            return None

        raw_time = record.get("time")
        time_info: dict[str, Any] = raw_time if isinstance(raw_time, dict) else {}
        timestamp_seconds = self._as_float(time_info.get("timestamp"))
        occurred_at = int(timestamp_seconds * 1000)
        timestamp_repr = str(time_info.get("repr", "")) or str(timestamp_seconds)

        raw_level = record.get("level")
        level_info: dict[str, Any] = raw_level if isinstance(raw_level, dict) else {}
        level = _LEVEL_MAP.get(str(level_info.get("name", "INFO")).upper(), "info")

        message = str(record.get("message", ""))
        extra = record.get("extra")
        metadata = dict(extra) if isinstance(extra, dict) else None
        source = record.get("name") or record.get("module")
        component = str(metadata["component"]) if metadata and "component" in metadata else None

        stack_trace: str | None = None
        if record.get("exception"):
            stack_trace = str(payload.get("text", "")).strip() or None

        return LogEntry(
            id=self._build_id(line, occurred_at),
            occurred_at=occurred_at,
            timestamp=timestamp_repr,
            level=level,
            message=message,
            component=component,
            source=str(source) if source is not None else None,
            metadata=metadata,
            stack_trace=stack_trace,
        )

    @staticmethod
    def _as_float(value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _build_id(line: str, occurred_at: int) -> str:
        digest = hashlib.sha1(line.encode("utf-8")).hexdigest()[:12]
        return f"{occurred_at}-{digest}"


__all__ = ["LogEntry", "LogFileReader"]
