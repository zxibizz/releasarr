# Integrations

Every external service the backend talks to, what it asks for, and how it behaves when
unconfigured. Adapters live in `src/infrastructure/<service>/`; the ports they implement are in
`src/application/interfaces/`.

## At a glance

| Service | Setting | Default | Required URL suffix | Unconfigured |
| --- | --- | --- | --- | --- |
| Sonarr | `RELEASARR_SONARR_URL` | `http://localhost:8989/api/v3` | `/api/v3` | Client exists, errors on first call |
| Radarr | `RELEASARR_RADARR_URL` | `http://localhost:7878/api/v3` | `/api/v3` | Client exists, errors on first call |
| Prowlarr | `RELEASARR_PROWLARR_URL` | *(empty)* | `/api/v1` | reports `is_configured = False`; the indexer endpoints and release search raise |
| qBittorrent | `RELEASARR_QBITTORRENT_URL` | *(empty)* | `/api/v2` | reports `is_configured = False`; the release operations raise, the scheduler's steps skip |
| TVDB | `RELEASARR_TVDB_BASE_URL` | `https://api4.thetvdb.com/v4` | v4 root | reports `is_configured = False`; use cases degrade |
| TMDB | `RELEASARR_TMDB_BASE_URL` | `https://api.themoviedb.org/3` | `/3` | reports `is_configured = False`; use cases degrade |

**Base URLs are passed through verbatim.** `ProwlarrReleaseSearchService` requests `/search`
and `QbittorrentClient` requests `/torrents/add`, so the configured value must already carry
`/api/v1` or `/api/v2`. Getting this wrong produces a 404 from the provider, not a startup
error.

Degradation is decided once, in `src/core/container.py`, not at the call site. This is why the
app boots with nothing configured.

Where a provider is optional per deployment the port itself says so: `IndexerDirectory`,
`TvdbService`, `TmdbService`, `ReleaseSearchService`, `ReleaseDownloadService` and
`ReleaseLifecycleService` each declare `is_configured`, and the adapter answers from the
settings it was built with, so a caller branches on a value instead of on an absent object.

Nothing stands in for a provider that is missing. A stub cannot download, and one that
answered successfully made a misconfigured deployment look like a working one, so a public
endpoint reports the missing configuration instead and a background step skips its work.
What counts as configured differs per service: Prowlarr needs both URL and key; TVDB and TMDB
need only the key, since their base URLs always have a default; qBittorrent needs URL,
username and password.

## The shared HTTP client

`src/infrastructure/http/base.py` backs Sonarr, Radarr, Prowlarr, and TMDB. Not qBittorrent
(session cookies, own retry logic) and not TVDB (bearer token flow via `httpx.Auth`).

| Behaviour | Value |
| --- | --- |
| Default timeout | 15s |
| Attempts | 3 (2 retries) |
| Backoff | `0.2 * 2^attempt` seconds |
| Retried on | Transport errors, and status `429`, `500`, `502`, `503`, `504` |
| Failure | `HttpClientError`, mapped to HTTP 502 by `DOMAIN_ERROR_MAP` |

Every client takes a `transport` parameter so tests can inject `httpx.MockTransport`. Keep it
when adding one.

## Sonarr

`SonarrHttpClient` implements `SonarrService`. Auth is `X-Api-Key` on every request; an empty
key raises `HttpClientError` at call time with the name of the env var to set.

| Method | Path | Used for |
| --- | --- | --- |
| GET | `/series` | The whole library, with per-season counts and monitoring, for `sonarr_sync` |
| GET | `/series/{id}` | Series details for the add-request flow |
| GET | `/series/lookup` | Search (`term=…`) and TVDB lookup (`term=tvdb:{id}`) |
| POST | `/series` | Add a series |
| PUT | `/series/{id}` | Apply season monitoring |
| GET | `/episode` | Episodes for a series, with files |
| DELETE | `/series/{id}` | Delete a series nothing is wanted from |
| GET | `/rootfolder`, `/qualityprofile` | Library folders and profiles for the add flow |
| POST | `/manualimport` | Import preview, to validate before committing |
| POST | `/command` | Queue the `ManualImport` command (`importMode: copy`) |
| GET | `/command/{id}` | Poll that command |

Things that will surprise you:

- **`/series` is the sync's only read**, and it is not paginated. The wanted list is not
  consulted at all: a season with every aired episode filed is absent from it, and releasarr
  still wants a request for it. The sweep adopts every monitored season, refreshes the rows it
  already has, and deletes the rows whose season or series is no longer monitored or no longer
  there. An empty answer prunes nothing — that reading is a restarting Sonarr, not a wiped
  library.
- **`wait_for_series_episodes`** polls `/series/{id}` every second for up to 30s after an add,
  because Sonarr both populates episodes and settles monitoring asynchronously. It returns once
  the requested seasons report episodes *and* `addOptions` has gone from the payload — Sonarr
  clears those last, after the post-add pass has rewritten season and episode monitoring, so
  anything read or written before that is overwritten seconds later. A timeout is *not* an
  error — it returns whatever it last read, so the caller must cope with an incomplete season
  list and with `has_add_options` still set.
- **`_await_command`** polls for up to 300s and treats a timeout as success. A slow Sonarr
  therefore looks like a successful import.
- **`manual_import` swallows HTTP errors and returns `False`.** The export use case turns that
  into a raised `RuntimeError`, which is what increments `export_failures_count`.
- **Adding a series posts the lookup payload back verbatim**, with
  `searchForMissingEpisodes: false` — Releasarr grabs releases itself and must not have Sonarr
  racing it.
- **The add names no monitoring strategy, and that is deliberate.** Sonarr applies the
  `seasons` flags of the same payload only when `addOptions.monitor` is left out; naming one
  replaces them wholesale, and `all` — the reading that sounds right for "monitor the episodes
  of these seasons" — marks every season monitored once the series is scanned (the post-add
  pass runs `SetEpisodeMonitoredStatus` with the strategy, and every season holding a monitored
  episode is flagged monitored). Both `IgnoreEpisodes*` flags are sent as `false` because they
  default to `on`, and either one on leaves the flagged seasons' episodes unmonitored, so they
  stay out of Sonarr's wanted list and out of our own sync.
- **The add is checked afterwards rather than trusted.** What Sonarr ends up monitoring is its
  own decision, taken after the scan that follows the add, and a season selection it does not
  apply is invisible until the next sync adopts every monitored season it finds as a request of
  its own. `AddMediaRequestUseCase._confine_to_requested_seasons` reads the settled series back
  and unmonitors anything outside the request, logging a warning when it has to. Only a series
  just added is corrected this way: nothing else can have monitored those seasons a moment ago,
  so nothing of the user's is taken away.
- **`apply_season_monitoring` is additive and safe**: monitor wins over unmonitor, seasons not
  mentioned keep their current flag.
- **`delete_series` is asked for only after reading the series back and finding it empty**: no
  season monitored, no future-seasons flag, no episode file, and no request of ours still naming
  it. It never asks Sonarr to delete files, and Sonarr answers a delete with an empty 200, which
  is why it goes through `request_no_content` rather than the JSON helper.
- Lookup results for series already in the library carry a non-zero `id`; absent ones report
  `id: 0`. That is how the discover flow knows what is already in Sonarr.
- The manual-import preview sends `quality: {quality: {id: 0}}` and `languages: []` so Sonarr
  infers both from the filename rather than accepting a guess.

## Radarr

`RadarrHttpClient` implements `RadarrService`. Same `X-Api-Key` auth, same retry, command
polling, and error-swallowing behaviour as Sonarr.

| Method | Path | Used for |
| --- | --- | --- |
| GET | `/movie` | The whole library, with `hasFile` and `monitored`, for `radarr_sync` |
| GET | `/movie/{id}` | Movie details for the add-request flow |
| GET | `/movie/lookup` | Search and TMDB lookup (`term=tmdb:{id}`) |
| POST | `/movie` | Add a movie |
| PUT | `/movie/{id}` | Set `monitored` |
| DELETE | `/movie/{id}` | Delete a movie nothing is wanted from |
| GET | `/rootfolder`, `/qualityprofile` | Add flow |
| POST | `/manualimport`, `/command`, GET `/command/{id}` | Import and poll |

Radarr-specific:

- **`minimumAvailability: "released"`** on add. The sync no longer reads the wanted list, so
  this only governs when Radarr itself starts searching; anything stricter would leave a movie
  Radarr monitors — and releasarr tracks — out of Radarr's own queue.
- `addOptions.searchForMovie: false`, for the same reason as Sonarr.
- `set_movie_monitored` no-ops when the flag already matches.
- **`delete_movie`** is the counterpart of Sonarr's `delete_series`, asked for on the same
  reading: a movie with no file of its own and no request of ours left. Files are never deleted.

## Prowlarr

`ProwlarrReleaseSearchService` implements `ReleaseSearchService`. Auth is `X-Api-Key`. Timeout
is `RELEASARR_PROWLARR_TIMEOUT`, default 20s — longer than the shared default because an
indexer sweep is slow.

| Method | Path | Used for |
| --- | --- | --- |
| GET | `/search` | `query`, `type=search`, plus one `categories` param per configured category |
| GET | *(absolute URL)* | `fetch_torrent()` against a result's `downloadUrl` |

Result mapping, which is where the field names stop matching:

| Prowlarr | Record |
| --- | --- |
| `guid` | `release_id` — and later the `releases.id` primary key |
| `title` | `release_name` |
| `magnetUrl` / `downloadUrl` | `magnet_link` / `torrent_file_url` |
| `infoUrl` | `info_url` |
| `indexer` | `source` |
| `publishDate` | `publish_date` (`Z` normalized to `+00:00`) |

A result is **dropped** if it has no `title` or `guid`, or if it has neither a magnet nor a
download URL — there would be nothing to grab. Results are sorted by seeders descending, then
name.

`ReleaseSearchResultRecord.query` is the one field that is not Prowlarr's: it is the query the
search was made with, carried on every result so a grab can record what found the release.

Three behaviours worth knowing:

- **Results are cached in memory** by `release_id` on every successful search, and
  `resolve(release_id)` reads only that cache. `QueueReleaseDownloadUseCase` relies on this to
  turn the id the UI posted back into a grabbable result, which means **a grab must follow a
  search in the same process lifetime.** A restart between the two loses the result.
- **Magnet vs torrent file:** the grab prefers `torrent_file_url`, fetches it, and parses the
  torrent to get the info hash *and the file list*. Only if that fails does it fall back to the
  magnet — and a magnet carries no file list, so the mapping UI comes up empty. See
  [`file-mapping.md`](file-mapping.md).
- **"All indexers unavailable" is not an error, unless the search was scoped to one indexer.**
  On a 400, the body is checked for `"all selected indexers"`. Unscoped (`indexer_id=None`),
  that matches and an empty result set is returned instead of raising. Scoped to a single
  indexer, the same message means that indexer is down, and `search()` raises
  `ReleaseSearchUnavailableError` instead. Any other 400 propagates as `HttpClientError`.

### Searching indexers one at a time

`SearchReleaseSourcesUseCase` does not make Prowlarr's own aggregate `/search` call. Instead it
calls `ProwlarrIndexerDirectory.list_indexers()`, keeps the ones that are `enabled` and
`supports_search`, and fans out one `search(query, indexer_id=...)` per indexer under an
`asyncio.Semaphore`. This exists because Prowlarr's own sweep serializes on whichever indexer
answers last, so one dead indexer stalls (and, with the shared HTTP client's retries, re-stalls)
every search. Each indexer instead gets its own timeout and retry budget:

| Setting | Default | Env var |
| --- | --- | --- |
| Per-indexer timeout | `10.0`s | `RELEASARR_PROWLARR_SEARCH_TIMEOUT` |
| Retries per indexer | `1` | `RELEASARR_PROWLARR_SEARCH_RETRIES` |
| Concurrent indexers | `5` | `RELEASARR_PROWLARR_SEARCH_CONCURRENCY` |

Retries live in the use case, not `BaseHttpClient`: `ProwlarrReleaseSearchService.search()` calls
`BaseHttpClient.request(..., retries=0)`, so a use-case-level retry never becomes a
client-level retry on top of it. Results from every indexer that answered are merged and
re-sorted by seeders; indexers that time out or raise `ReleaseSearchUnavailableError` after
exhausting their retries are reported back as `failed_indexers` on `ReleaseSearchResponse`
rather than failing the whole search. `list_indexers()` itself failing (Prowlarr unreachable)
still fails the request with a 502 — there is no per-indexer list to fall back to.

An indexer Prowlarr is currently backing off (`derive_health(...) is IndexerHealth.BLOCKED`,
i.e. `disabled_till` in the future) is reported as failed **without being queried at all** —
Prowlarr would refuse it anyway, so attempting it would only spend the timeout budget. A
`DEGRADED` indexer (past failures, not currently backed off) is still attempted.

When Prowlarr is not configured, the use case raises `ProwlarrNotConfiguredError` (503). There is
no stand-in search service to answer instead, and an empty result set would read as "no results"
rather than "no Prowlarr".

A completed search logs `Release search completed` with the query, the result count, and how many
indexers were searched and failed, bound with `request_id=` when the search was run from a
request — that binding is what puts the line on the request's `/logs` activity view. The
per-indexer lines (`Skipping indexer blocked by Prowlarr`, `Indexer search failed`) carry the same
binding, so a partial failure is visible there too.

`ReleaseRegrapper` (`application/use_cases/releases/regrab.py`, driven by both
`RegrabOutdatedReleasesUseCase` and the on-demand refresh) scopes the same way: it maps a
release's stored `torrent_source` (the indexer name Prowlarr reported at grab time) back to an
indexer id via `list_indexers()`, and searches only that indexer instead of sweeping all of
them. An unknown name, or a directory that cannot be read, means the check is skipped with a
warning bound to the release's requests — not widened to the unscoped sweep, which would put the
query to every tracker at once and is what the sweep's pacing exists to avoid. Nothing is
written about it either way: no answer was received, so there is nothing to warn a user about.
If that search raises `ReleaseSearchUnavailableError` (the indexer is
banned or not responding), it does not treat it as a bug: it logs a warning against every
request the release belongs to (`request_id=`, picked up by that request's `/logs` activity
view), and persists a `regrab_indexer_unavailable` row per request in `request_warnings` (see
[`docs/data-model.md`](../../../docs/data-model.md#request_warnings)) scoped to that one release
via `RequestWarningRepository.replace_for_releases`. The next release the loop checks is
unaffected either way — a request with several releases must not have one release's fresh
failure wiped out just because a sibling release answered.

The row clears the moment that same release gets a valid search response again, match or not;
it is not tied to the release actually changing.

A search that *does* answer, but returns no result carrying the release's own id, is the other
way this check fails: the indexer dropped the release or reissued it under a new one. That
persists `release_not_listed` with `{indexer}` in `details`, scoped and cleared the same way,
except that only finding the release again clears it — an indexer answering without it is
precisely the condition, so clearing on any valid response would make the row unreachable.

The replacement itself is then read before it is queued: one extra `fetch_torrent` per *actual*
re-grab, paid for only once the hash comparison has already decided the download happens. It is
used for the file check alone — the download still goes out as whatever the search result carried
— and it is what lets the release's stored files follow the new torrent (see
[`file-mapping.md`](file-mapping.md#re-grabbing-a-release)). A replacement that does not carry
every file the release already has is refused before anything is queued
(`ReleaseRegrabRejectedError`) and flagged with `regrab_files_missing`; one whose file list cannot
be read is downloaded without that reconciliation and leaves both file codes alone. That refusal
also removes the release from the sweep's candidates until the row clears — a release whose
replacement the indexer keeps reissuing short a file is retried by the on-demand refresh rather
than by the sweep.

`mapping_overlap` (see `application/use_cases/releases/warnings.py`) is the third code sharing
this table, written by `RequestWarningSynchronizer` instead — that one clears per-request rather
than per-release, since it is recomputed over a request's whole release set at once.

Every step of that check is logged against each request holding the release, not just the two
failures: `ReleaseRegrapper._log_for_requests` emits the record per `request_id`, so a sweep
nobody watched still leaves `Checking release for updates` (naming the indexer and the replayed
query) followed by its outcome — `Release is up to date on its indexer`, `Release is no longer
listed by its indexer`, or the re-grab itself — on the request's activity view. The check writes
no summary line — the per-release record is the summary — and `SyncSteps.regrab` only reports
itself when there was no candidate release to check at all.

### Indexer health

`ProwlarrIndexerDirectory` implements `IndexerDirectory`, backing the indexers page. Same base
URL and auth as the search service, resolved separately in `ServiceContainer.indexer_directory`.

| Method | Path | Used for |
| --- | --- | --- |
| GET | `/indexer` | Every indexer: `enable`, `protocol`, `privacy`, `priority`, `supports*`, `indexerUrls` |
| GET | `/indexerstatus` | Only the ones Prowlarr is backing off: `disabledTill`, `mostRecentFailure`, `initialFailure` |
| GET | `/indexer/{id}` | The definition to post back to `test` |
| POST | `/indexer/test` | Body is that definition verbatim |
| POST | `/indexer/testall` | No body; returns `[{id, validationFailures}]` |

Four things about this pair of endpoints are easy to get wrong:

- **`/indexerstatus` is a failure log, not a status list.** It holds nothing for a healthy
  indexer, so an empty array means everything is fine rather than nothing is known. The
  `status` field on `/indexer` looks like it would save the second call, but Prowlarr does not
  populate it reliably on the list route.
- **The `********` round-trip is deliberate.** Prowlarr masks api-key and password fields when
  it hands out a definition, and `SchemaBuilder.ReadFromSchema` restores the stored value when
  it reads that sentinel back against the resource `id`. So posting the definition unchanged
  tests with real credentials; stripping or rewriting the masked fields would break it.
- **`testall` answers 400 when any indexer fails,** carrying the same per-indexer body as a
  success. The status code is a summary, so the body is parsed either way. It also skips
  indexers that are switched off.
- **Health is derived in the use case, not here.** The adapter reports raw flags and
  timestamps; `derive_health` compares `disabled_till` against now. A cleared `enable` outranks
  the failure log, because that is a deliberate choice rather than a back-off that expires.

**An unconfigured Prowlarr raises** `ProwlarrNotConfiguredError` (503), here and on release
search. This page exists to answer "are my indexers working", and an empty list reads as "no
indexers" rather than "no Prowlarr".

## qBittorrent

Three classes, split by concern:

| Class | Role |
| --- | --- |
| `QbittorrentClient` | Low-level Web API wrapper. Implements no application port. |
| `QbittorrentReleaseDownloadService` | `ReleaseDownloadService` — add, delete, resolve save path |
| `QbittorrentReleaseLifecycleService` | `ReleaseLifecycleService` — pause, resume |

| Method | Path | Used for |
| --- | --- | --- |
| POST | `/auth/login` | Form login with username and password |
| POST | `/torrents/add` | Magnet (`urls`) or uploaded `.torrent` (`fileselect[]`) |
| POST | `/torrents/pause`, `/torrents/resume` | By lowercased hash |
| GET | `/torrents/info` | One torrent by hash, or a list filtered by category/tag |
| POST | `/torrents/delete` | By hash, with `deleteFiles` |

**Auth is a session cookie, not a key.** The client logs in lazily, and on a `403` it clears
its session, logs in again, and retries the request once. That single retry is the whole
recovery story.

**Identity is the info hash, never the release id.** A `releases.id` is a Prowlarr GUID — often
a forum URL — so every qBittorrent call uses `info_hash`, parsed from the magnet when the
release row is created. `QbittorrentReleaseLifecycleService` takes a parameter named
`release_id` but is passed the info hash by its caller.

**Adds** set `autoTMM: false`, `contentLayout: Original`, and apply the optional
`savepath`, `category`, and tags. Tags always include the `request_id`, prefixed with
`RELEASARR_QBITTORRENT_TAG_PREFIX` when set, which is what makes Releasarr's torrents findable
in the qBittorrent UI.

**The download directory for export** comes from `get_download_directory(info_hash)`: the
torrent's own `save_path` if `/torrents/info` reports one, otherwise the configured
`RELEASARR_QBITTORRENT_SAVE_PATH`. This is the value joined onto each file's relative path to
build the absolute path Sonarr and Radarr import from, which is why **Releasarr and the *arrs
must see the same filesystem**.

Error handling here is deliberately lenient, because a half-failed torrent operation should not
block the database from being tidied: `pause`/`resume` return `False`, `get_torrent` returns
`None`, `list_torrents` returns `[]`, and `delete_torrent` swallows errors including 404. Only
`add` raises.

When the client reports itself unconfigured, the scheduler skips release sync entirely and
records `reason: qbittorrent_not_configured` rather than failing the job. The public release
operations instead raise `QbittorrentNotConfiguredError` (503): a pause or a grab that quietly
did nothing is worse than one that says why it could not.

## TVDB

`TvdbHttpClient` implements `TvdbService`. Used for series metadata and the discover search.

| Method | Path | Used for |
| --- | --- | --- |
| POST | `/login` | Token exchange, body `{"apiKey": …}` |
| GET | `/series/{id}/extended` | Series metadata with `meta=translations` |
| GET | `/search` | Series search (`type=series`) |
| POST | `/web/search/queries` | `follower_count` for the search hits — see below |

**The v4 token flow** lives in a private `_TvdbAuth(httpx.Auth)`: on the first authenticated
request it posts the API key to `/login`, reads `data.token`, and sends
`Authorization: Bearer …` thereafter. Double-checked locking with an `asyncio.Lock` keeps
concurrent callers to one login. The token is cached for the client's lifetime and **there is
no refresh on 401** — only the initial login exists, so an expired token means restarting the
process.

TVDB does not use `BaseHttpClient`, so it gets no retries.

Season handling: only seasons with `type.type == "official"` are returned, which is broadcast
order and matches what Sonarr uses. Translations are filtered to the configured languages;
passing an empty language list yields no translations at all rather than everything.

A TVDB failure during sync is logged, cached as `None` for that run, and the sync continues with
Sonarr-only metadata. Discover search is stricter and raises
`MetadataProviderUnavailableError` for series when TVDB is absent.

**Follower counts come from an endpoint TVDB does not document.** Discover search ranks hits
partly by popularity, and `/v4/search` carries none: the `score` field that holds it lives only
on `/series/{id}`, and v4 offers no way to batch or sort by it, so reading it there would mean
one request per hit. `POST /web/search/queries` is the Algolia index behind thetvdb.com's own
search box, and it returns `follower_count` inline — the same number `/series/{id}` reports as
`score`. It takes an object-valued `params` rather than Algolia's usual query string:

```json
{"requests": [{"indexName": "TVDB", "params": {"query": "…", "filters": "type:series", "hitsPerPage": 20}}]}
```

It sits outside `/v4`, takes no API key, and appears in no published schema, so it is wired up
as an enrichment and never as a source of results. `search_series` issues it concurrently with
`/v4/search` — about 45ms on top of a 260ms search rather than the sum — and `_follower_counts`
returns `None` on any failure, whereupon `_popularity` falls back to counting how many languages
the series has been translated into. That proxy is coarser but tracks a following closely enough
to order a result list, and it comes free with the `/v4/search` response.

The fallback is all-or-nothing by design: a result set must be scored on one scale, or hits end
up ranked by which signal happened to be available for them. A hit the index simply does not
know gets `0`, which is where an entry below the index's own cutoff belongs anyway.

## TMDB

`TmdbHttpClient` implements `TmdbService`.

| Method | Path | Used for |
| --- | --- | --- |
| GET | `/movie/{id}/translations` | Localized titles and overviews |
| GET | `/search/movie` | Movie search |

**Auth is dual-mode, chosen by inspecting the token's shape**: a value containing a `.` is
treated as a v4 JWT and sent as `Authorization: Bearer …`; anything else is a v3 key and is
merged into every request as an `api_key` query param.

It deliberately **never fetches the base `/movie/{id}` record**. Radarr already supplies title,
poster, and genres; TMDB is only asked for what Radarr cannot provide. Poster URLs in search
results are built client-side from `https://image.tmdb.org/t/p/w500` plus `poster_path`.

## Metadata languages

`RELEASARR_METADATA_LANGUAGES` defaults to `("eng", "rus")`. Three-letter ISO 639-2 is the
canonical storage form, and it reaches the `media_requests.localizations` JSON column in that
form.

The providers disagree on codes, so `src/application/utility/languages.py` bridges them —
`to_two_letter` / `to_three_letter`, accepting both terminological and bibliographic variants
(`deu`/`ger`) and stripping locale suffixes (`pt-BR` → `pt`). TVDB speaks three-letter codes
natively; TMDB speaks two, so the client converts in both directions and takes the first
non-empty value when a language has regional variants (`en-US` and `en-GB`).

`src/application/utility/localization.py` decides what lands in the flat `title` and `overview`
columns: `LocalizationPicker` prefers the configured languages in order, falls back to any
available translation, and finally to what the *arr app reported.
`merge_default_localization` folds the *arr's own title and overview into the `eng` slot, so a
request always has something to display even with no metadata provider configured.

## Shutdown

`AppContainer.shutdown()` calls `aclose()` on any resolved service that has one — tvdb, tmdb,
sonarr, radarr, release_search — and closes the qBittorrent client. A new adapter holding an
`httpx.AsyncClient` should expose `aclose()` and be added to that list.
