# Operational Tasks

Background work is a set of tasks that reuse the shared container and
infrastructure wiring. The scheduler runs them on intervals; the API queues
them on demand. There is no task CLI — a one-off run is
`POST /tasks/run/{kind}`, which the scheduler picks up within a few seconds.

## The Task Set

Five tasks make up all recurring work. They are defined once, in
`src/application/use_cases/tasks/definitions.py`, and shared by the scheduler
and the API so the UI can never disagree with what actually runs.

| Task | Default interval | What it does |
| --- | --- | --- |
| `sonarr_sync` | 60m | Reconcile requests with the seasons Sonarr monitors |
| `radarr_sync` | 60m | Reconcile requests with the movies Radarr monitors |
| `release_sync` | 30s | Refresh download progress and state from qBittorrent |
| `export` | 5m | Import finished releases into Sonarr and Radarr; also queued the moment one finishes |
| `regrab` | 10m | Re-download releases the indexer has since replaced, in paced batches |

The order above is significant: `export` can only import releases that
`release_sync` has already marked completed.

The five intervals are the schedule, not the only thing that makes a task run.
Two of them are also queued by work that just happened: the release sync queues an
`export` when a download turns completed, and saving file mappings queues one when
its release has already finished. Both are described under
[On-Demand Runs](#on-demand-runs-api-triggered).

`release_sync` also recomputes derived request state — `status`, `mapping_overlap` warnings, and
`newest_release_published_at` — for every request that has releases, via
`RecomputeRequestStateUseCase`. This is the same recompute every release-lifecycle use case
(grab, delete, remap, replace, regrab, export, and the on-demand refresh) calls directly, so
`release_sync` exists here as a periodic sweep that catches drift those write-through call sites
missed, not as the primary way a request's state stays current.

The same pass reconciles releases whose torrent qBittorrent no longer lists: each one is stamped
`missing_since` on first absence, and an in-flight release still missing past
`RELEASARR_RELEASE_MISSING_GRACE_SECONDS` is failed, which the recompute then propagates to its
requests. An already-exported release is skipped outright — seeding ends with removal by design,
and `regrab` adds a fresh torrent when there is a better copy. A listing that comes back
completely empty is distrusted and stamps nothing, because the sync reads only its configured
category and the alternative reading is "every torrent vanished at once".

## Background Scheduler (separate worker)

Runs each task on its interval and drains the jobs queued over the API. This is
a standalone worker process and is deliberately NOT started inside the FastAPI
app, keeping the web process free of implicit background schedulers. Run it
alongside the API under your process manager (systemd, Kubernetes, etc.):

```bash
uv run python -m src.tasks.scheduler_service
```

It reuses the shared application container, so it picks up the same settings,
logging, and (single, shared) qBittorrent client as the API.

Each interval is measured from the last execution recorded in the
`scheduled_tasks` table, so a restart does not reset the schedule. Scheduled
runs update that row (last execution, duration, status, error) rather than
writing a job history row, which keeps a 30-second task from producing thousands
of rows a day.

## Re-grab pacing

The sweep asks a tracker to search again for every release it checks, and a
client that asks too much at once gets throttled. It is therefore bounded twice
over:

- **Per indexer, per run.** Each indexer gets an allowance of
  `min(ceil(its backlog / 5), RELEASARR_MAX_REGRABS_PER_INDEXER_PER_EXECUTION)`,
  so the whole backlog is spread evenly over five runs unless the ceiling makes
  that impossible (default ceiling 20). A backlog that already fits the ceiling is
  taken in one run — spreading it would only delay a check that costs the tracker
  the same either way.
- **Per indexer, in time.** Two checks against the same indexer are kept at least
  `RELEASARR_REGRAB_INDEXER_DELAY_SECONDS` apart (default 2s). The gap is per
  tracker, so a backlog on one of them does not hold up the others.

Both are editable at runtime under **Settings → Tasks**.

The rotation is what makes a per-run allowance fair. Candidates come back ordered
by `releases.regrab_checked_at` with the never-checked first, and the sweep stamps
that column for every release it looked at — including the ones it only skipped,
or they would spend their indexer's allowance again on every run after this one.
A release therefore goes to the back of its indexer's queue once checked, so each
run takes the ones that have waited longest and the rest are left for the next.

So a release is re-checked every `ceil(backlog / allowance)` runs: with 300
candidates on one tracker and the defaults, that is 15 runs (20 per run, the
ceiling binding), i.e. about two and a half hours at the ten-minute interval;
raise the ceiling if that is slower than wanted. A backlog that fits the ceiling
is covered in the single run that checks it, so a small library is re-checked
every ten minutes as before.

The check itself is always scoped to the release's own indexer, and a release
whose indexer Prowlarr no longer lists is skipped rather than searched for
unscoped: an unscoped query puts the search to every configured tracker at once,
which is the load this pacing exists to avoid. That skip is logged per request
and writes no warning, since no answer was received.

## On-Demand Runs (API triggered)

The API and the scheduler are separate processes, so "run now" is a queued job
rather than a direct call: `POST /tasks/...` writes rows to `sync_jobs` and the
scheduler claims them within a few seconds. Each endpoint returns `202` with a
`Location` header pointing at `/tasks/jobs/{jobId}`.

| Endpoint | Tasks queued | Intended caller |
| --- | --- | --- |
| `POST /tasks/run/{kind}` | The named task | Run button on the tasks page |
| `POST /tasks/sync_all` | All five, in order | "Run all tasks" button, operators |
| `POST /tasks/sync_downloads` | `release_sync`, `export` | Download client on torrent completion |

Saving file mappings queues an `export` too, whenever the release they belong to
has already finished downloading. Remapping is how a wrong or missing import
gets corrected, and the payload is on disk by then, so the fix applies at once
instead of waiting out the 5-minute interval. Failing to queue it is logged and
otherwise ignored: the mappings are stored regardless, and the scheduled run is
still coming.

The release sync does the same for a download that just finished. A torrent
reaching full progress is the one moment the export has something new to do, and
it happens on a schedule of its own, so `SyncReleasesTask` reports how many
releases moved into `completed` and the step queues an `export` for them. A batch
of torrents finishing at once collapses onto one job, and the enqueue carries the
`download_client` trigger so it reads the same as one that arrived over the API.
The periodic run stays: it is what retries an import that failed, picks up
releases that completed before this existed, and covers an enqueue that could not
be written.

One job runs one task, so a `sync_all` queues five jobs. The response tracks the
last of them, since that finishing means the whole sequence is done.

Poll `GET /tasks/jobs/{jobId}` for a single job, or `GET /tasks/jobs?limit=n`
for recent history (capped at 100, newest first, trimmed to the most recent 200
finished jobs). Each job records its summary in `result` and, on failure, the
message in `error`. A failing job does not stop the ones behind it in the queue.

`GET /tasks/scheduled` reports every task with its interval, last execution,
last duration, and computed next execution. It lists all five tasks even before
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
variable, so the five task loops running side by side each keep their own value.

Two things are tagged in addition to the step itself:

- On-demand runs also carry `job_id` and `trigger`, so a row in the Queue
  section can be traced to the exact lines it produced.
- Scheduled runs carry the task name on the scheduler's own outcome lines.
  Those runs write no job history, so those lines are all the logs view has for
  them.

The endpoint reads and parses whole log files per call, so prefer a task filter
over paging through everything.

### Lines a task writes about a request

A task working on one request's row binds `request_id`, which is what puts its
lines on that request's activity view and not only in the task's own log. The
re-grab check is the pattern to copy: `ReleaseRegrapper` runs per release for
both the sweep and the on-demand refresh, and every way out of one check
writes a record per request holding that release — nothing moved, the indexer no
longer lists the release, no hash could be read, the torrent was replaced, the
indexer would not answer, the indexer is not configured any more. A check that
found nothing to do is still the answer to "what happened to this request", and
the sweep is the only thing that ever looked, so it is logged rather than
passed over.

The sweep's own outcome is the exception. With no release in hand there is no
`request_id` to attach, so `No releases to check for updates` is only reachable
under `?task=regrab` or `?service=scheduler`.

### Which process logged a line

The API and the scheduler are separate processes writing their own files, so
every record names the one that produced it: `configure_logging` binds `service`
once per process rather than making each call site remember, and
`GET /logs?service={api|scheduler}` splits them. The CLI task commands count as
the scheduler — they run the same work the loops do, without the loop.

A `task` filter already implies the scheduler, because only work done inside a
task binds `task` and all of it runs in the worker. The logs page shows the task
in a record's expandable context rather than as a filter of its own; the process
is a dropdown, not a tab, so the page is one merged stream.

Every record also names the part of the codebase that wrote it. `get_logger`
requires a `LogComponent`, so a module cannot log without one, and
`GET /logs?component=…` filters on it. The values are namespaced by the layer
(`api.*`, `scheduler.*`, `task.*`, `usecase.*`, `integration.*`), which is what
the page groups its component filter by.

Records written before the processes tagged themselves carry no `service` at all.
The reader falls back to the presence of `task` for those, so upgrading does not
blank out the history already on disk.

### Filtering by severity

`GET /logs?min_level={debug|info|warning|error}` is a floor rather than an exact
match: `warning` returns warnings and errors. Loguru's seven levels are collapsed
onto these four while the file is parsed, so `_LEVEL_SEVERITY` in the reader is
what orders them — the names alone would not say that `CRITICAL` outranks
`WARNING`. `debug` is the floor everything clears, so asking for `info` is how the
request lines below are kept out of the view.

The logs page keeps the chosen floor in `localStorage` rather than in the URL,
because it is a preference about the reader rather than part of one view: someone
who only wants errors wants them whatever the process, and after a reload.

### The API's own request lines

uvicorn has access logging, but its loggers are configured with
`propagate: false` and a handler of their own, so nothing it writes reaches
Loguru and the file this endpoint reads never saw a request line.
`register_request_logging` logs them instead: one record per request with
`status_code` and `duration_ms` on it, `api.auth` for the auth routes and
`api.http` for the rest. They are logged at DEBUG - below the file sink's INFO
floor - because one line per request is mostly the UI's own polling and refresh
chatter, so the logs page stays readable unless `RELEASARR_LOG_LEVEL=DEBUG`
opts back in.

Only the path is recorded, never the query string: the redaction patcher rewrites
the message and not the metadata, and this file is served to the browser by the
endpoint itself.

### How far back the logs view reaches

Each file sink rotates at 10 MB, which moves history into a timestamped sibling
(`backend.log` becomes `backend.2026-09-13_04-54-26_300466.log`). The reader
follows those siblings so a rotation no longer empties the view, but only as far
back as `RELEASARR_LOG_HISTORY_FILES` allows (default 3, counting the active
file). The budget is per file, so it bounds what each process contributes.
Raising it widens the window at the cost of a slower read, since every call scans
each file it is allowed to reach.

The sink also records at INFO even when `RELEASARR_LOG_LEVEL` is higher, because
a request's activity view is built from these records and should not go quiet
when an operator turns the console down. A lower setting still applies, so
`DEBUG` reaches the file too.

### Each process keeps its own file

s6-overlay supervises the scheduler and uvicorn as separate processes, and each
writes its own file: `RELEASARR_LOG_FILE` for the API and
`RELEASARR_SCHEDULER_LOG_FILE` for the scheduler. They used to share one, which
meant that when either rotated it, the other carried on writing to the file it
already held open — now a renamed sibling — so records landed outside the active
file at unpredictable moments. Splitting them removes that race rather than
working around it.

The cost is that the reader has to merge two timelines. It reads both files and
sorts by time, which is what keeps `?request_id=` useful: the API logs accepting a
request and the scheduler logs the work that request queued, so a single request's
activity spans both files and neither alone would answer.

### Hooking up qBittorrent

The release sync notices a finished torrent within its 30-second interval and
queues the export itself, so this hook is optional: it shaves those seconds off
by reporting the completion directly. Point qBittorrent's completion hook at
`sync_downloads` in **Options → Downloads → Run external program on torrent
finished**:

```bash
curl -fsS -X POST -H "X-API-Key: $RELEASARR_SERVICE_KEY" http://releasarr:8000/api/tasks/sync_downloads
```

Substitute your own host and the service API key (visible, and rotatable, under `/service-key`,
or **System → Users** in the UI); the `/api` prefix is what nginx serves the API under. The narrow endpoint is deliberate: a full sync on every torrent would hit
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
