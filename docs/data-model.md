# Data model

Schema defined in `services/backend/src/domain/models.py`, enums in
`services/backend/src/domain/enums.py`, migrations in `services/backend/alembic/versions/`.
SQLite by default, PostgreSQL via `asyncpg`.

## Tables

```
media_requests ──┬── release_request_links ──┬── releases ── release_files
                 │   (many-to-many)          │                    │
                 └───────────────────────────────── mapped_request_id
                     (SET NULL)

users ──┬── media_requests.owner_user_id      (SET NULL)
         ├── refresh_tokens.user_id           (CASCADE)
         └── service_api_keys.user_id         (CASCADE)

sync_jobs         standalone: one row per on-demand task run
scheduled_tasks   one row per task kind, holding its schedule state
```

Logs are **not** in the database. `/logs` parses Loguru's JSON file sink through
`infrastructure/logs/reader.py`.

### `media_requests`

One movie, or one season of one series. `id` is a 64-char string (application-generated, not a
sequence).

Shared: `media_type`, `status`, `title`, `year`, `overview`, `poster_url`, `genres` (JSON list),
`localizations` (JSON dict), `runtime_minutes`, `imdb_id`, `created_at`, `updated_at`,
`exported_at`.

Series-only: `season_number`, `total_episodes`, `aired_episodes`, `downloaded_episodes`,
`series_title`, `series_year`, `sonarr_series_id`. Movie-only: `radarr_movie_id`.

`aired_episodes` and `downloaded_episodes` are Sonarr's `episode_count` and
`episode_file_count` for the season, written by every sync. They are stored rather than derived
so the API never has to ask Sonarr for them, and nullable so rows that predate the columns
report `episode_counts: null` instead of a misleading "nothing downloaded". The API derives the
three numbers the UI shows from them — downloaded, pending (`aired − downloaded`, clamped at
zero) and unaired (`total − aired`, clamped at zero) — in
`application/use_cases/requests/mappers.py`. `downloaded_episodes` is also set to
`aired_episodes` when a season stops being missing, since Sonarr only drops a season from that
list once it has everything.

`exported_at` is stamped by the `export` task at the moment Sonarr or Radarr accept a release's
files for that request, and is what the request card shows on its left. It is deliberately set
for partly-filled seasons too — the question it answers is "when did this last reach the arr",
not "when did it finish" — and stays NULL when the arr filled the request by itself, which is
not an export by releasarr.

Constraints, and what they mean:

| Constraint | Encodes |
| --- | --- |
| `ck_media_requests_movie_series_fields` | A movie row must have `season_number` and `total_episodes` NULL. |
| `uq_media_requests_sonarr_series_season` | One request per Sonarr series + season. This is what makes `sonarr_sync` idempotent. |
| `uq_media_requests_radarr_movie` | One request per Radarr movie, for the same reason. |

`localizations` is `{ "eng": {"title": …, "overview": …}, "rus": {…} }`, populated from TVDB/TMDB
according to `RELEASARR_METADATA_LANGUAGES`. The frontend reads it per UI locale and does not
fall back across languages.

`owner_user_id` is a nullable FK to `users.id` (`SET NULL`). NULL means the request has no
owning user — the state every request created by `sonarr_sync`/`radarr_sync` starts in and stays
in unless an admin reassigns it, or a human added it themselves through `/discover/requests`, in
which case it is set once, at creation, and never overwritten by a later sync (see
`sync_sonarr.py`/`sync_radarr.py`'s `owner_user_id` parameter, applied only on the
`existing is None` branch). A request without an owner is visible only to a caller whose
effective scope is unrestricted (an admin, or a user with `can_view_all_requests`) — see
"Ownership and permissions" below.

### `releases`

One tracked torrent. `id` is a `String(512)` because it is the Prowlarr GUID, commonly a forum
URL; `name` is `Text()` because tracker titles routinely exceed 255 characters once they list
dubs, episode ranges, and release notes. Both widths were set by migration `e1f36b8ac704` after
the originals overflowed.

Identity: `info_hash`, `size_bytes`, `torrent_source`, `quality`, `info_url` (the tracker's own
page for the release, when the indexer reported one; `regrab` refreshes it alongside `name`).
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

### `users`

`id` is a UUID hex string. `username` is unique and always stored lower-cased. `password_hash`
is an Argon2 hash (`pwdlib`) — never the plaintext, never logged. `role` is `admin` or `user`;
an admin bypasses every flag below unconditionally (`has_permission()` in
`application/use_cases/auth/permissions.py`). The four `can_access_*` / `can_view_all_requests`
booleans gate one `Permission` each. `allowed_root_folders` is a JSON list of paths; **empty
means unrestricted**, not "nothing allowed" — the same convention `RequestScope` and
`ListRootFoldersUseCase` use. `failed_login_attempts` and `locked_until` back the login lockout
(`RELEASARR_AUTH_MAX_FAILED_LOGINS` / `RELEASARR_AUTH_LOCKOUT_SECONDS`).

### `refresh_tokens`

One row per issued refresh token; only `token_hash` (SHA-256 of the opaque token) is stored, so a
database leak alone cannot mint a session. `family_id` is shared by every token born from one
login: rotating keeps the family id, and presenting an already-rotated (`revoked_at` set) token
revokes the whole family — the standard response to refresh-token reuse, which most plausibly
means the token was stolen. `remember` records whether "remember me" was checked at login, so
rotation can preserve the original session length instead of collapsing it to a browser session.

### `service_api_keys`

At most one row: the single key (`key`) that authenticates via `X-API-Key`. Stored and shown in
plaintext — it isn't a password, and an admin needs to read it back into whatever integration
uses it, the same as Sonarr/Radarr's own API key. It is not bound to a user — authenticating with
it always yields a full admin `Principal`, the same way Sonarr and Radarr's API keys aren't scoped
to an account. It's generated automatically the first time it's needed
(`GetOrCreateServiceApiKeyUseCase`, run at API startup) rather than created through the UI, and
`RegenerateServiceApiKeyUseCase` replaces it outright — there is no per-key revoke, only rotation.

## Ownership and permissions

`RequestScope` (`application/use_cases/auth/permissions.py`) is the one thing that decides which
media requests a caller may see: `unrestricted()` for an admin or `can_view_all_requests`, else
`owned_by(user.id)`. It is threaded into `MediaRequestRepository.list_requests` as
`owner_user_id`, and checked after a single-resource fetch via `scope.permits(owner_user_id)`.
An out-of-scope request 404s rather than 403s — a 403 would confirm the row exists.

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
| `UserRole` | `admin`, `user` |

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
| `1c2d3e4f5a6b` | Create `users`, `refresh_tokens`, `service_api_keys` |
| `2d3e4f5a6b7c` | Add `media_requests.owner_user_id` |

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
