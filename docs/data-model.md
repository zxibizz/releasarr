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

media_requests ──┬── request_warnings ──── releases
                 │   (request_id, release_id both nullable-on-release FKs)

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
`exported_at`, `newest_release_published_at`.

Series-only: `season_number`, `total_episodes`, `aired_episodes`, `downloaded_episodes`,
`series_title`, `series_year`, `sonarr_series_id`. Movie-only: `radarr_movie_id`.

`aired_episodes` and `downloaded_episodes` are Sonarr's `episode_count` and
`episode_file_count` for the season, written by every sync. They are stored rather than derived
so the API never has to ask Sonarr for them, and nullable so rows that predate the columns
report `episode_counts: null` instead of a misleading "nothing downloaded". The API derives the
three numbers the UI shows from them — downloaded, pending (`aired − downloaded`, clamped at
zero) and unaired (`total − aired`, clamped at zero) — in
`application/use_cases/requests/mappers.py`. The missing-seasons refresh is not the only writer:
the sweep that settles a season Sonarr no longer reports as missing stores Sonarr's own
`episode_count` and `episode_file_count` in the same pass that decides its status, since leaving
the missing list is what stops the counts being refreshed — and `pending` is derived from them,
so a stale `downloaded_episodes` reads as an episode still to fetch. Where the sweep has no
answer for a season, the stored counts stand and `downloaded_episodes` falls back to
`aired_episodes`, because Sonarr only drops a season from that list once it has everything.

Leaving Sonarr's missing list is not the same as being finished: a season that is still airing
leaves it every week and returns when the next episode is wanted. A request is therefore only
completed once there are neither pending nor unaired episodes left, and one with episodes still
to air goes back to `pending` rather than closing — which is also what keeps it actionable for a
release grabbed by hand, since `regrab` has no indexer result to refresh it from. An
`ArrCompletion` carries `has_unaired` for exactly that reason: both arrs call a season complete
once its aired episodes hold files, so a verdict that admits unaired episodes is not taken as
final and falls through to the release rules instead.

`status` has exactly one place that decides what a request's releases and its arr imply:
`RequestStateDeriver` (`application/use_cases/requests/state.py`), invoked through
`RecomputeRequestStateUseCase` (`application/use_cases/requests/recompute_state.py`). Sonarr and
Radarr are the only authority on `completed` — the sync use cases pass their verdict in as an
`ArrCompletion`, and no other code path is allowed to set or clear that status. Everything else
the release set implies — `downloading`, `importing`, `failed`, `monitoring`, and falling back
to `pending` once nothing is left in flight or worth regrabbing — is derived from the linked
releases alone. `importing` is a completed release still waiting on the arr: the download is
done and the import has not landed, which reads very differently from an actual transfer when
the import is stuck. The one direct write of `status` outside the recompute is user intent:
explicitly re-requesting a completed season or movie reopens it to `pending`, which no verdict
can express — the next sync's verdict settles it again.
The recompute also settles `MAPPING_OVERLAP` warnings and `newest_release_published_at` in the
same pass, since all three depend on the same release set. It runs synchronously from every
release-lifecycle use case (grab, delete, remap, replace, regrab, export) and from the
`release_sync` task, so a request's card does not wait for the next scheduled sync to catch up —
including when a request's last release is deleted, which used to leave it stuck on its last
status forever.

Once a request has nothing in flight but still holds a release sourced from an indexer, the
recompute moves it to `monitoring` rather than leaving it `pending`: that release is what
`regrab` looks for candidates against, and a hand-grabbed release never qualifies.

`newest_release_published_at` is the latest `releases.published_at` linked to the request, kept
in sync by the same recompute rather than computed at read time — storing it lets a future filter
or sort use it in SQL without joining every request's releases.

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

`search_query` is what the indexer was searched with when this release was grabbed, and what
`regrab` searches with again. `name` is the tracker's own title, which some trackers' search
cannot match, so a check that searched it reported a listed release as `release_not_listed`. The
column is NULL for releases grabbed before it existed and for hand-supplied ones — neither has a
query to replay — and the check falls back to `name` for those.

Live stats, refreshed by `release_sync`: `status`, `progress`, `download_speed`, `upload_speed`,
`seeders`, `leechers`, `ratio`, `added_at`, `completed_at`.
Export bookkeeping: `last_exported_info_hash`, `export_failures_count`.
Client reconciliation: `missing_since`.

`missing_since` is when qBittorrent first stopped reporting the torrent, cleared the moment it
reappears. qBittorrent is the only writer of a release's status, so a removed torrent would
otherwise leave the row at its last-known state forever — including `completed`, which pins its
request on `importing`. Past `RELEASARR_RELEASE_MISSING_GRACE_SECONDS` (default 900s), an
in-flight release whose torrent is still absent is failed. An already-exported one is not
tracked at all: the arr has the files, the torrent was removed after seeding, and `regrab` adds
a fresh one when the indexer has something better. A cycle in which qBittorrent lists no
torrents at all stamps nothing: the sync reads only its own category, so that can also mean the
client was re-categorised, not that the whole library vanished.

`last_exported_info_hash` is how `regrab` and `export` cooperate. The export queue is every
release that is `completed`, has `export_failures_count < 5`, and whose `last_exported_info_hash`
is either NULL or different from its current `info_hash` — so a repack that changes the hash
becomes eligible for import again, and a release that has failed five times stops being retried.
The fifth failure also fails the release: dropping it out of the queue alone would leave the row
`completed` and in flight, which is the same pin as a vanished torrent. A re-grab therefore also
puts the release back to `downloading`, `progress` 0, no completion time, and no missing stamp:
the row cannot go on being eligible while the files the new torrent is downloading are still
replacing the old ones. It becomes `completed` again when the replacement finishes and the next
`release_sync` reads that back.

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

### `request_warnings`

One row per (request, release, code) — a condition worth surfacing on a request but not worth
blocking on. `release_id` is nullable, for a future request-only code that names no release.
`code` is `mapping_overlap`, `regrab_indexer_unavailable`, `release_not_listed`,
`regrab_files_unmapped`, or `regrab_files_missing`; `details` is a JSON blob whose shape is
code-specific (`{file_ids, related_release_ids}` for an overlap, `{reason}` for an indexer that
could not be asked, `{indexer}` for one that dropped the release, `{file_ids, file_count}` for a
replacement whose new files nobody could place, `{missing_files, file_count}` for one that was
refused because it dropped a file the release already had).

| Code | Written by | Cleared by |
| --- | --- | --- |
| `mapping_overlap` | `RequestWarningSynchronizer`, called from every mapping-changing use case (`UpdateReleaseFileMappingsUseCase`, `ReleaseGrabFinalizer.auto_map_files`, `DeleteReleaseUseCase`, `ExistingReleaseReplacer`) and a reconcile pass folded into `release_sync` | A recompute over the request's whole release set that no longer finds the release in an overlapping bucket — see `RequestWarningSynchronizer.sync_for_requests` |
| `regrab_indexer_unavailable` | `ReleaseRegrapper` — driven by the scheduled `regrab` sweep and by `RefreshRequestReleasesUseCase` — on `ReleaseSearchUnavailableError` | The same check, the next time that release's own search returns a valid response, whether or not anything changed |
| `release_not_listed` | `ReleaseRegrapper`, same two callers, when the indexer answers but no result carries the release's own id | The same check, once a result matches that id again. An indexer that could not be asked leaves the row alone: an answer nobody got disproves nothing |
| `regrab_files_unmapped` | `ReleaseRegrapper`, same two callers, when the replacement torrent added files and automapping placed none of them | The next re-grab that reconciles the release and places at least one of its new files — or leaves it with none — and `UpdateReleaseFileMappingsUseCase`, once every file the row names carries a mapping |
| `regrab_files_missing` | `ReleaseRegrapper`, same two callers, when the replacement torrent does not carry a file the release already has and the re-grab is therefore refused | A later check whose replacement does carry every stored file. A check that could not read a file list leaves the row alone, for the same reason an unanswered search does. While it is set, `get_potential_outdated_releases` leaves the release out of the sweep's candidates — the row is the exclusion — so only the on-demand refresh retries it |

The codes are deliberately not all scoped the same way — see
[`services/backend/docs/integrations.md`](../services/backend/docs/integrations.md#searching-indexers-one-at-a-time)
for why `mapping_overlap` clears per-request while the four written by the re-grab check clear
per-release.

**Removal is explicit, not left to the FK cascade.** `ondelete="CASCADE"` is set on both FKs for
Postgres correctness, but nothing relies on it: SQLite does not enforce foreign keys (there is no
`PRAGMA foreign_keys=ON` anywhere), and unlinking a release that is shared between requests
violates no FK at all — the row it should clear is scoped by a link table, not by either parent
being deleted. `DeleteReleaseUseCase` and `ExistingReleaseReplacer` both call
`RequestWarningRepository.delete_for_release`/`delete_for_request_release` themselves.

`GET /requests?has_warnings=` filters with an `EXISTS` subquery against this table rather than a
join, so a request with several warning rows is not duplicated in the page.

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
login: rotating keeps the family id, and presenting a token that was already rotated away revokes
the whole family — the standard response to refresh-token reuse, which most plausibly means the
token was stolen. A replay within `RELEASARR_AUTH_REFRESH_REUSE_GRACE_SECONDS` of that rotation is
the one exception, and only while the family still has a live token: a browser's tabs share one
refresh cookie, so two requests can be sent with it before either response replaces it, and the
loser of that race is not a thief. `remember` records whether "remember me" was checked at login,
so rotation can preserve the original session length instead of collapsing it to a browser session.

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
| `MediaRequestStatus` | `pending`, `searching`, `downloading`, `monitoring`, `importing`, `completed`, `failed` |
| `ReleaseStatus` | `pending`, `downloading`, `completed`, `failed` |
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
| `dfed8040c181` | Add `media_requests.newest_release_published_at`, backfilled from releases |
| `e5b3c7d9a1f2` | Add the `release_not_listed` label to the `request_warning_code` enum |
| `d4b8c1f60a72` | Add the `regrab_files_unmapped` and `regrab_files_missing` labels to the `request_warning_code` enum |
| `7a1f5c2e9d43` | Add `releases.search_query` |

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
