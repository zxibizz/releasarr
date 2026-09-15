"""Matching a release's stored files against a replacement torrent's file list."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from src.application.interfaces.releases import FileReconciliation, ReleaseFileRecord
from src.application.utility.release_parsing import natural_sort_key


def reconcile_release_files(
    existing: Sequence[ReleaseFileRecord],
    incoming: Sequence[ReleaseFileRecord],
) -> FileReconciliation:
    """Match the files a release already has against the ones a torrent declares.

    A repack carries the same files under the same relative paths, so an exact
    path is the match that matters. A group that renamed only the torrent's root
    folder would otherwise make every stored file look missing, which is why the
    leftovers are compared by name as well - and only when the two sides carry
    the same number of files under it, so two ``01.mkv`` in different seasons are
    never paired by luck.
    """

    incoming_by_path: dict[str, list[ReleaseFileRecord]] = defaultdict(list)
    for record in incoming:
        incoming_by_path[_path_key(record)].append(record)

    matched: list[tuple[str, ReleaseFileRecord]] = []
    leftovers: list[ReleaseFileRecord] = []
    for record in existing:
        bucket = incoming_by_path.get(_path_key(record))
        if bucket:
            matched.append((record.id, bucket.pop(0)))
            continue
        leftovers.append(record)

    unmatched = [record for bucket in incoming_by_path.values() for record in bucket]

    stored_by_name = _group_by_name(leftovers)
    torrent_by_name = _group_by_name(unmatched)

    missing: list[ReleaseFileRecord] = []
    for name, records in stored_by_name.items():
        candidates = torrent_by_name.get(name, [])
        if len(candidates) != len(records):
            missing.extend(records)
            continue
        for record, candidate in zip(
            sorted(records, key=_sort_key),
            sorted(candidates, key=_sort_key),
            strict=True,
        ):
            matched.append((record.id, candidate))

    taken = {record.id for _, record in matched}
    added = [record for record in unmatched if record.id not in taken]

    return FileReconciliation(matched=matched, added=added, missing=missing)


def _group_by_name(files: Sequence[ReleaseFileRecord]) -> dict[str, list[ReleaseFileRecord]]:
    grouped: dict[str, list[ReleaseFileRecord]] = defaultdict(list)
    for record in files:
        grouped[_name_key(record)].append(record)
    return grouped


def _path_key(record: ReleaseFileRecord) -> str:
    """A file's torrent-relative path, comparable across platforms and case."""

    return (record.path or record.name).replace("\\", "/").casefold().strip("/")


def _name_key(record: ReleaseFileRecord) -> str:
    return _path_key(record).rsplit("/", 1)[-1]


def _sort_key(record: ReleaseFileRecord) -> tuple[str | int, ...]:
    return natural_sort_key(_path_key(record))


__all__ = ["reconcile_release_files"]
