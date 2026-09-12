# Operational Tasks

The new backend ships with standalone async tasks that reuse the shared
container and infrastructure wiring. These tasks can be executed alongside the
FastAPI app using `uv run`.

## Release Summary

Outputs a JSON payload describing how many releases exist in the system grouped
by status. Useful for dashboards or smoke checks during operations.

```bash
uv run python -m src.tasks.cli release-summary --json
```

Without `--json`, the command prints a human-readable summary instead.

The task relies on the same database configuration specified in the
`AppSettings`, so ensure environment variables are set before running it.

## Sync Sonarr Requests

Imports Sonarr missing seasons into media requests (enriched with TVDB
metadata when configured).

```bash
uv run python -m src.tasks.cli sync-sonarr-requests
```

## Sync Radarr Requests

Imports Radarr missing movies into media requests (enriched with TMDB
metadata when configured).

```bash
uv run python -m src.tasks.cli sync-radarr-requests
```

## Sync Releases

Refreshes release download stats (progress, speeds, seeders, status) from
qBittorrent. Requires the `RELEASARR_QBITTORRENT_*` environment variables.

```bash
uv run python -m src.tasks.cli sync-releases
```

## The Task Set

Five tasks make up all recurring work. They are defined once, in
`src/application/use_cases/tasks/definitions.py`, and shared by the scheduler
and the API so the UI can never disagree with what actually runs.

| Task | Default interval | What it does |
| --- | --- | --- |
| `sonarr_sync` | 60m | Import Sonarr's missing episodes as media requests |
| `radarr_sync` | 60m | Import Radarr's missing movies as media requests |
| `release_sync` | 30s | Refresh download progress and state from qBittorrent |
| `export` | 5m | Import finished releases into Sonarr and Radarr |
| `regrab` | 60m | Re-download releases the indexer has since replaced |

The order above is significant: `export` can only import releases that
`release_sync` has already marked completed.

## Background Scheduler (separate worker)

Runs each task on its interval and drains the jobs queued over the API. This is
a standalone worker process and is deliberately NOT started inside the FastAPI
app, keeping the web process free of implicit background schedulers. Run it
alongside the API under your process manager (systemd, Kubernetes, etc.):

```bash
uv run python -m src.tasks.cli scheduler
# equivalent to:
uv run python -m src.tasks.scheduler_service
```

It reuses the shared application container, so it picks up the same settings,
logging, and (single, shared) qBittorrent client as the API.

Each interval is measured from the last execution recorded in the
`scheduled_tasks` table, so a restart does not reset the schedule. Scheduled
runs update that row (last execution, duration, status, error) rather than
writing a job history row, which keeps a 30-second task from producing thousands
of rows a day.

## On-Demand Runs (API triggered)

The API and the scheduler are separate processes, so "run now" is a queued job
rather than a direct call: `POST /tasks/...` writes rows to `sync_jobs` and the
scheduler claims them within a few seconds. Each endpoint returns `202` with a
`Location` header pointing at `/tasks/jobs/{jobId}`.

| Endpoint | Tasks queued | Intended caller |
| --- | --- | --- |
| `POST /tasks/run/{kind}` | The named task | Run button on the tasks page |
| `POST /tasks/sync_all` | All four, in order | "Run all tasks" button, operators |
| `POST /tasks/sync_downloads` | `release_sync`, `export` | Download client on torrent completion |

One job runs one task, so a `sync_all` queues four jobs. The response tracks the
last of them, since that finishing means the whole sequence is done.

Poll `GET /tasks/jobs/{jobId}` for a single job, or `GET /tasks/jobs?limit=n`
for recent history (capped at 100, newest first, trimmed to the most recent 200
finished jobs). Each job records its summary in `result` and, on failure, the
message in `error`. A failing job does not stop the ones behind it in the queue.

`GET /tasks/scheduled` reports every task with its interval, last execution,
last duration, and computed next execution. It lists all four tasks even before
the scheduler has registered them, so the UI works on a fresh install.

Requests for a task that is already queued collapse onto the waiting job, so a
batch of torrents finishing at once produces a single run of each task. When a
sequence is queued, a task is only reused if doing so preserves the order —
an `export` already waiting ahead of a new `release_sync` gets its own job
instead, so the import never runs before the sync that feeds it.

## Task Logs

`GET /logs?task={kind}` returns everything logged while that task was running,
including lines emitted by use cases several layers below the task itself. That
works because `SyncSteps.for_kind` binds the task name for the duration of the
step, and every path that runs a task goes through it — no call site has to
remember to pass the task along.

The binding uses Loguru's `contextualize`, which is backed by a context
variable, so the four task loops running side by side each keep their own value.

Two things are tagged in addition to the step itself:

- On-demand runs also carry `job_id` and `trigger`, so a row in the Queue
  section can be traced to the exact lines it produced.
- Scheduled runs carry the task name on the scheduler's own outcome lines.
  Those runs write no job history, so those lines are all the logs view has for
  them.

The endpoint reads and parses the whole log file per call, so prefer a task
filter over paging through everything.

### Hooking up qBittorrent

Point qBittorrent's completion hook at `sync_downloads` so finished torrents are
imported into Sonarr and Radarr immediately instead of waiting for the 5-minute
export loop. In **Options → Downloads → Run external program on torrent
finished**:

```bash
curl -fsS -X POST -H "X-API-Key: $RELEASARR_API_KEY" http://releasarr:8000/api/tasks/sync_downloads
```

Substitute your own host and key; the `/api` prefix is what nginx serves the API
under. The narrow endpoint is deliberate: a full sync on every torrent would hit
Sonarr, Radarr, the metadata providers, and the indexers far more often than
necessary.

Runs triggered this way show up in the Queue section of **System → Tasks** in
the web UI, tagged with the download client as their trigger, and their log
lines are filterable by task in the Logs section on the same page.

Note that the export only picks up releases whose status is `completed`, which
the release sync derives from qBittorrent reporting full progress and a
completion timestamp (a finished torrent keeps seeding, so its reported state
cannot be used for this).

## Adding New Tasks

1. Implement the task in `src/tasks/` using async functions where you can reuse
   container-provided dependencies.
2. Expose the task helpers from `src/tasks/__init__.py` so they can be imported
   in tests or other tooling.
3. Provide a unit test under `tests/tasks/` that exercises the task logic with
   lightweight fakes for infrastructure dependencies.
4. Document the command invocation in this file so operators can discover it.
