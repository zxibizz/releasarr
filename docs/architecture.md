# Architecture

How the pieces fit together, and why they are arranged this way. Read this before
[`backend.md`](backend.md) or [`frontend.md`](frontend.md).

## Process model

Three processes, one container image:

```
        ┌─────────────────────────────────────────────┐
        │  nginx  :80                                 │
        │    /        → /static  (built frontend)     │
        │    /api/    → localhost:8000  (prefix       │
        │               stripped by trailing slash)   │
        └──────────────────┬──────────────────────────┘
                           │
        ┌──────────────────▼──────────┐   ┌───────────────────────────┐
        │  uvicorn  :8000             │   │  scheduler worker         │
        │  src.api.app:app            │   │  src.tasks.scheduler_…    │
        │                             │   │                           │
        │  enqueues rows in sync_jobs │──▶│  claims them, runs tasks  │
        └─────────────────────────────┘   └───────────────────────────┘
```

[s6-overlay](https://github.com/just-containers/s6-overlay) is PID 1 and supervises all three.
`/etc/cont-init.d/01-migrations` runs `alembic upgrade head` before anything starts — a failure
there takes the container down rather than serving against a stale schema — and the three
services in `/etc/services.d` come up afterwards, each restarted on its own if it dies. The tree
lives in `cicd/containers/all-in-one/root/`, copied to `/` at build time.

Each service has a `log/run` that pipes it through `s6-log`, which tags every line with `[api]`,
`[scheduler]`, or `[nginx]` — otherwise one container's stream mixes three processes with no way
to tell them apart. The `run` scripts start with `exec 2>&1` because s6 pipes only fd 1 to the
logger, and both uvicorn and Loguru write to stderr. nginx is pointed at `/dev/stdout` and
`/dev/stderr` for the same reason, which also stops it filling `/var/log/nginx` inside the
container, where nothing rotates it.

nginx also sets the cache headers the built frontend depends on. `/sw.js`, `/index.html` and the
manifest are always revalidated — a cached service worker would pin a browser to a build the
server no longer has, with no later deploy able to reach it — while `/assets/` is immutable,
which is safe because Vite hashes those names. That same location answers a missing asset with a
404 instead of the SPA fallback, so a stale `index.html` cannot hand the browser HTML where it
expects JavaScript. See [`../services/frontend/docs/pwa.md`](../services/frontend/docs/pwa.md).

Two details of that arrangement look like faults and are not. s6 warns at boot that
`/etc/s6-overlay/s6-rc.d` is empty, because the services use the older `services.d` layout — four
shell scripts rather than the sixteen files the `s6-rc` format needs for the same three daemons
and one init step. And `docker stop` reports exit code 137 even when shutdown was orderly, since
s6 ends its own halt sequence with a kill.

`docker-compose.dev.yaml` keeps the same split but gives each process its own container with the
source bind-mounted and reload enabled, and lets the Vite dev server stand in for nginx and the
built bundle — it proxies `/api` with the prefix stripped exactly as nginx does, so the two
environments agree on URLs.

**The API never executes background work.** `POST /tasks/…` writes `sync_jobs` rows and returns
`202` with a `Location` header; the scheduler picks them up within seconds. This keeps the web
process free of implicit schedulers, and means "run now" behaves identically whether it came
from the UI, an operator, or qBittorrent's completion hook.

Because the two processes write one file each, records never interleave on disk and a rotation in
one cannot move the other's history. The reader merges the two files by time, which is what makes a
request's activity view complete: the API logs accepting the request and the scheduler logs the work
it queued. See [`../services/backend/docs/tasks.md`](../services/backend/docs/tasks.md).

The API also logs its own requests rather than leaving that to uvicorn, whose loggers do not
propagate into Loguru — so a request and the work it went on to trigger are both on disk, each
tagged with the process that wrote it.

## The contract

`openapi.yaml` at the repo root is the single source of truth for the HTTP surface. Three
consumers:

| Consumer | How it uses the spec |
| --- | --- |
| Backend | `tests/api/test_openapi_contract.py` asserts FastAPI's generated spec covers every operation in the document. Pydantic schemas in `src/schemas/` mirror it by hand — there is no Python codegen. |
| Frontend | `npm run codegen` regenerates `src/lib/api/generated/types.ts` with `openapi-typescript`. `src/types.ts` re-exports the schemas the app uses. |
| Mock server | `services/frontend/mock-server/` implements the same document, and serves it at `/openapi.yaml`. |

Note the prefix asymmetry: the spec's `servers` entry is `/api` because that is what nginx
serves under, but FastAPI mounts routes at `/requests`, `/discover`, and so on. The app itself
has no `/api` prefix.

## Authentication and authorization

Every request carries one of two credentials: an `Authorization: Bearer` access token (a human
session, 15 minutes, issued by `/auth/login`) or an `X-API-Key` service key (long-lived, always
admin — for the bot and similar integrations, not bound to any particular user). Both resolve to
the same `Principal` (`src/application/use_cases/auth/permissions.py`), which is what every route
depends on via `require_user` / `require_admin` / `require_permission(...)` — see
[`backend.md`](backend.md#auth-and-permissions).

A session's refresh token is the one piece of this that is not a bearer token: it lives in an
httpOnly cookie (`releasarr_refresh`, path `/api/auth`, set by `POST /auth/login|refresh`), so
`services/frontend/src/lib/api/client.ts` never touches it directly. It reads the access token
from memory instead, and reacts to a `401` by refreshing once and retrying. That refresh is the
client's `refreshSession()`, used by `AuthProvider`'s bootstrap too, so however many requests 401
at once — or however many times React StrictMode mounts the provider — the server is asked to
rotate the cookie once. See [`frontend.md`](frontend.md#auth).

Permissions are flat and per-user, not role hierarchies: `role` is `admin` or `user`, and four
independent booleans (`view all requests`, `tasks`, `indexers`, `logs`) plus a root-folder
allow-list apply only to `user`. An admin bypasses every one of them. `media_requests.owner_user_id`
is the one piece of data this all gates — NULL for a request no human owns (everything
`sonarr_sync`/`radarr_sync` create, plus anything added via the service key), set once at
creation for anything a signed-in user adds, and reassignable afterwards only by an admin. See
[`data-model.md`](data-model.md#ownership-and-permissions).

Before any of this exists, `GET /auth/setup` reports whether a first admin still needs to be
created; the frontend's `RequireAuth` sends a browser there instead of `/login` until one has
been.

## Backend layers

Dependencies point inward. Nothing in `application/` may import FastAPI, SQLAlchemy models, or
`infrastructure/`.

```
src/
  api/               FastAPI routers, auth dependency, exception handlers.
                     Thin: schema → command → use case → DTO → schema.
  schemas/           Pydantic models at the HTTP boundary. All extend APIModel.
  application/
    use_cases/       One class per operation, grouped by area.
                     commands.py (input) / dto.py (output) / mappers.py / exceptions.py
    interfaces/      Protocols the use cases depend on, plus the record dataclasses
                     those protocols pass around.
    queries/         Read models that bypass use cases (logs, release summary).
    utility/         Torrent name parsing, file matching, language codes, UNSET sentinel.
  infrastructure/    The implementations: sonarr/, radarr/, prowlarr/, qbittorrent/,
                     tvdb/, tmdb/, http/ (BaseHttpClient), logs/ (file reader),
                     and the SQLAlchemy repositories.
  domain/            models.py (ORM entities) and enums.py. No behaviour.
  db/                Declarative Base, DBManager (session/transaction), repository base.
  tasks/             Task step implementations, the scheduler worker, a Typer CLI.
  core/              container.py (DI composition root) and logging.py.
  settings/          AppSettings (pydantic-settings, RELEASARR_ prefix).
```

Two properties this buys, both load-bearing:

**Integrations degrade rather than crash.** Because ports are `Protocol`s, an unconfigured
provider still arrives as an object that reports `is_configured`, so no call site handles `None`
and nothing pretends to work in its place. The app boots and the UI works; only grabbing and
downloading are inert, and they say so.

**Use cases are testable without HTTP or a database.** `tests/fakes.py` provides protocol
implementations backed by dicts, so use case tests construct the class directly.

## Frontend structure

Feature-sliced. Each slice owns its endpoints and its React Query keys.

```
src/
  features/
    requests/    api.ts, queries.ts, filtering.ts, useRequestFilters.ts,
                 localization.ts, pages/, components/
    releases/    api.ts, queries.ts, components/, fileMapping/
    discover/    api.ts, queries.ts, keys.ts, pages/, components/
    tasks/       api.ts, queries.ts, pages/  (also hosts useSyncWatcher)
    logs/        api.ts, queries.ts, services.ts, useLogFilters.ts,
                 pages/ (tabbed by process), components/, LogsModal.tsx
  components/    Shared presentational pieces (StatusBadge, Panel, ResponsiveModal, …)
  lib/           api/client.ts (the only fetch wrapper), api/generated/, i18n.ts, queryClient.ts
  utils/         formatters, files, errors, status (the one place status colors live)
  hooks/         useIsMobile
  locales/       resources.ts — en + ru in one file
  router.tsx     Routes, lazy loading, loaders that warm the query cache
  App.tsx        AppShell, nav, useSyncWatcher
```

`queryClient.ts` sets a global `staleTime` of 30s. Polling is deliberately narrow: only
`features/tasks/queries.ts` sets `refetchInterval` (2s for active jobs, 10s for scheduled
tasks). `useSyncWatcher`, mounted once in `AppLayout`, watches those jobs and invalidates
`requestKeys.all` / `releaseKeys.all` when one finishes — which is how a completed background
import shows up in the UI without every page polling.

## How a request flows end to end

1. **`sonarr_sync` / `radarr_sync`** read missing seasons and movies from the *arrs, enrich them
   with TVDB/TMDB metadata, and upsert `media_requests` rows. Uniqueness is
   `(sonarr_series_id, season_number)` for series and `radarr_movie_id` for movies. For series
   they also own completion: a season Sonarr no longer reports missing is closed only once
   nothing is left to air, and one that is still airing is put back on `pending` instead.
2. **A human picks a release.** `GET /releases/search` proxies Prowlarr;
   `POST /requests/{id}/releases/download` hands the magnet or `.torrent` to qBittorrent and
   writes a `releases` row plus a `release_request_links` row. `ReleaseGrabFinalizer` marks the
   request `downloading` and runs the auto-mapper.
3. **`release_sync`** refreshes progress, speeds, seeders, and status from qBittorrent every 30
   seconds. A release becomes `completed` when qBittorrent reports full progress *and* a
   completion timestamp — a finished torrent keeps seeding, so its reported state alone cannot
   be used. One the export has already imported no longer counts as in flight, so a torrent
   that is only still there to seed cannot hold its request on `downloading`.
4. **Files get mapped.** `PUT /releases/{id}/files/mapping` stores, per file, a request plus
   (for series) a season and episode. `GET …/mapping/suggestions` offers the auto-mapper's
   guesses; the human confirms or overrides. Saving mappings for an already-finished release
   queues an `export` immediately rather than waiting out the interval.
5. **`export`** takes releases that are finished and not yet exported, resolves the download
   directory from qBittorrent, and calls Sonarr's and Radarr's manual import commands with
   absolute paths. It then asks both apps whether they now hold the request in full, and only
   closes the request if they say yes. Every request the import actually carried files for is
   stamped with an `exported_at`, including the ones that stay open because the release only
   covered part of a season.
6. **`regrab`** re-searches Prowlarr for tracked releases, compares info hashes, and
   re-downloads when the indexer has replaced the torrent (repacks).

Ordering matters: `export` can only import what `release_sync` has already marked completed,
which is why `sync_downloads` queues the two together and in that order.

## Deployment

`.forgejo/workflows/deploy.yml` runs `ruff check ./src` and `ruff format --check ./src`, builds
and pushes the image, then SSHes to pull and restart the compose stack. There is no test or
typecheck step in CI — run `uv run pytest` and `uv run mypy src` locally.
