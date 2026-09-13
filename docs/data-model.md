# Data model

Schema defined in `backend/src/domain/models.py`, enums in `backend/src/domain/enums.py`,
migrations in `backend/alembic/versions/`. SQLite by default, PostgreSQL via `asyncpg`.

## Tables

```
media_requests ──┬── release_request_links ──┬── releases ── release_files
                 │   (many-to-many)          │                    │
                 └───────────────────────────────── mapped_request_id
                     (SET NULL)

sync_jobs         standalone: one row per on-demand task run
scheduled_tasks   one row per task kind, holding its schedule state
```

Logs are **not** in the database. `/logs` parses Loguru's JSON file sink through
`infrastructure/logs/reader.py`.

### `media_requests`

One movie, or one season of one series. `id` is a 64-char string (application-generated, not a
sequence).

Shared: `media_type`, `status`, `title`, `year`, `overview`, `poster_url`, `genres` (JSON list),
`localizations` (JSON dict), `runtime_minutes`, `imdb_id`, `created_at`, `updated_at`.

Series-only: `season_number`, `total_episodes`, `series_title`, `series_year`,
`sonarr_series_id`. Movie-only: `radarr_movie_id`.

Constraints, and what they mean:

| Constraint | Encodes |
| --- | --- |
| `ck_media_requests_movie_series_fields` | A movie row must have `season_number` and `total_episodes` NULL. |
| `uq_media_requests_sonarr_series_season` | One request per Sonarr series + season. This is what makes `sonarr_sync` idempotent. |
| `uq_media_requests_radarr_movie` | One request per Radarr movie, for the same reason. |

`localizations` is `{ "eng": {"title": …, "overview": …}, "rus": {…} }`, populated from TVDB/TMDB
according to `RELEASARR_METADATA_LANGUAGES`. The frontend reads it per UI locale and does not
fall back across languages.

### `releases`

One tracked torrent. `id` is a `String(512)` because it is the Prowlarr GUID, commonly a forum
URL; `name` is `Text()` because tracker titles routinely exceed 255 characters once they list
dubs, episode ranges, and release notes. Both widths were set by migration `e1f36b8ac704` after
the originals overflowed.

Identity: `info_hash`, `size_bytes`, `torrent_source`, `quality`.
Live stats, refreshed by `release_sync`: `status`, `progress`, `download_speed`, `upload_speed`,
`seeders`, `leechers`, `ratio`, `added_at`, `completed_at`.
Export bookkeeping: `last_exported_info_hash`, `export_failures_count`.

`last_exported_info_hash` is how `regrab` and `export` cooperate. The export queue is every
release that is `completed`, has `export_failures_count < 5`, and whose `last_exported_info_hash`
is either NULL or different from its current `info_hash` — so a repack that changes the hash
becomes eligible for import again, and a release that has failed five times stops being retried
forever.

A release reaches `completed` only when qBittorrent reports full progress **and** a completion
timestamp. Its reported state is not usable for this, because a finished torrent keeps seeding.

### `release_files`

One file inside a release, plus its mapping.

Identity: `release_id` (FK, `CASCADE`), `name`, `size_bytes`, `path` (relative to the download
directory; `export` joins it onto the path qBittorrent reports).

Mapping: `mapping_type` (`movie` | `series` | NULL), `mapped_request_id` (FK, `SET NULL`),
`mapped_request_title`, `season`, `episode`.

| Constraint | Encodes |
| --- | --- |
| `ck_release_files_series_mapping` | A `series` mapping must carry both season and episode. |

`SET NULL` rather than `CASCADE` on `mapped_request_id` is deliberate: deleting a request should
orphan the mapping, not delete the file row, so the release stays inspectable and remappable.

### `release_request_links`

Composite primary key `(release_id, request_id)`, both `CASCADE`. Many-to-many because one
release can serve several requests — a complete-series pack, or a movie collection.

### `sync_jobs`

The hand-off between the API process and the scheduler process. `kind`, `status`, `trigger`,
`queued_at`, `started_at`, `finished_at`, `error`, `result` (JSON). Indexed on
`(status, queued_at)`, which is the claim query.

One job runs one task, so `sync_all` enqueues five rows. Scheduled runs are **not** recorded
here.

### `scheduled_tasks`

Primary key is `kind` — one row per task, not a history. `interval_seconds`, `last_execution`,
`last_duration_ms`, `last_status`, `last_error`.

Separate from `sync_jobs` so a 30-second task does not write thousands of rows a day, and so the
schedule survives a restart: each interval is measured from `last_execution`, not from process
start.

## Enums

Stored as their string values, not member names, via `build_enum()` in `models.py`.

| Enum | Values |
| --- | --- |
| `MediaType` | `movie`, `series` |
| `MediaRequestStatus` | `pending`, `searching`, `downloading`, `completed`, `failed` |
| `ReleaseStatus` | `pending`, `downloading`, `seeding`, `completed`, `failed` |
| `EpisodeStatus` | `downloaded`, `missing`, `unaired` |
| `SyncJobKind` | `sonarr_sync`, `radarr_sync`, `release_sync`, `export`, `regrab` |
| `SyncJobStatus` | `queued`, `running`, `completed`, `failed` |
| `SyncJobTrigger` | `api`, `download_client`, `schedule` |
| `RequestLogLevel` | `info`, `warning`, `error` |

`EpisodeStatus.MISSING` is the only one of its three that is actionable: it has aired and Sonarr
holds no file, which is exactly what a release is grabbed to fix.

These values are mirrored in `openapi.yaml` and reach the frontend through codegen, so renaming
one is a four-place change plus a migration.

## Migration history

| Revision | Change |
| --- | --- |
| `c2412e7b4945` | Create core tables |
| `2f6a6434600c` | Add `sonarr_series_id` |
| `9b51f749a7a1` | Add `localizations` |
| `a4c7e2b91f56` | Add Radarr movie support |
| `b7d4c91e2f08` | Create `sync_jobs` |
| `5a168e8321ab` | Add release export fields |
| `e1f36b8ac704` | Widen release text columns |
| `c58f2a91d374` | Add `scheduled_tasks` and per-task jobs |
| `d3e9a17c5b42` | Repair the `sync_job_kind` enum |

## The enum migration trap

`d3e9a17c5b42` exists because `c58f2a91d374` used `batch_alter_table` to change
`sync_job_kind`'s labels. On SQLite that works — enums are VARCHAR plus a CHECK constraint, and
the table is recreated. On PostgreSQL the same operation casts the column to its *existing*
native type and changes nothing, so production kept the old labels (`downloads`, `full`) while
the code expected the new ones.

When changing enum labels, branch on the dialect and write the Postgres path explicitly:

```python
if op.get_bind().dialect.name != "postgresql":
    return
# column → text, delete/rewrite invalid rows, DROP TYPE, CREATE TYPE, cast back
```

Adding a single label can use `ALTER TYPE … ADD VALUE IF NOT EXISTS`. Replacing the whole label
set needs the full rebuild.
