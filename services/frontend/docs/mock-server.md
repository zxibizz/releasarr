# Mock server

`mock-server/` is an Express app that implements [`../../../openapi.yaml`](../../../openapi.yaml) in
memory. It is how the UI is developed: `npm run dev:mock` runs it on `:8001` alongside Vite on
`:3000`, and the app cannot tell it from the real backend.

This is not a test double. Frontend tests mock `apiRequest` directly (see
[`../../../docs/testing.md`](../../../docs/testing.md)); the mock server exists for the dev server and
for the screenshots in the root README.

## Layout

| File | Contents |
| --- | --- |
| `index.ts` | Express wiring and every route handler |
| `store.ts` | `MockStore` — all mutable state and the behaviour behind it |
| `mockData.ts` | Seed requests, releases, and release files |
| `mockDiscover.ts` | The pretend Sonarr/Radarr library for the Add flow |
| `mockLogs.ts` | Seed request and task log lines |

Routes are thin and the store holds the behaviour, mirroring how the backend splits routers from
use cases. `index.ts` also serves the contract itself at `/openapi.yaml` and a `/__health`
endpoint the dev script waits on.

`MOCK_SERVER_PORT`, `MOCK_SERVER_ORIGIN`, and `MOCK_SERVER_API_PATH` override the defaults
(`8001`, `http://localhost:8001`, `/api`). The origin matters because async responses return an
absolute `location` URL.

## State

Everything lives in the single `mockStore` instance, so **state resets on restart** and Vite's
reload does not touch it. Seed collections are lazily cloned on first read:

```typescript
export class MockStore {
  private requestsCache: MediaRequest[] | null = null;
  private releasesCache: Release[] | null = null;
  private searchResultsByRequest: Record<string, ReleaseSearchResult[]> = {};
  private requestLogsByRequestId: Record<string, RequestLogEntry[]> = {};
  private taskLogsCache: RequestLogEntry[] | null = null;
  private syncJobs: SyncJob[] = [];
  // Cloned because adding media mutates it, standing in for the *arr library.
  private discoverCatalogue: DiscoverCatalogueEntry[] = DISCOVER_CATALOGUE.map((entry) =>
    clone(entry),
  );
```

Reads clone on the way out too, so a handler cannot hand the store's own objects to Express and
have them mutated later. Keep that discipline when adding state.

## Jobs advance on read, not on a timer

There are no `setTimeout`s. Every job-touching method calls `advanceSyncJobs()` first, which
recomputes each job's status from how much wall-clock time has passed since it was queued:

```typescript
  private advanceSyncJobs(): void {
    const now = Date.now();

    for (const job of this.syncJobs) {
      const queuedAt = new Date(job.queued_at).getTime();

      if (job.status === 'queued' && now - queuedAt >= MOCK_JOB_QUEUED_MS) {
        job.status = 'running';
        job.started_at = new Date(queuedAt + MOCK_JOB_QUEUED_MS).toISOString();
      }

      if (job.status === 'running') {
        const startedAt = new Date(job.started_at ?? job.queued_at).getTime();
        if (now - startedAt >= MOCK_JOB_RUNNING_MS) {
          job.status = 'completed';
          job.finished_at = new Date(startedAt + MOCK_JOB_RUNNING_MS).toISOString();
          job.duration_ms = MOCK_JOB_RUNNING_MS;
          job.result = MOCK_TASK_RESULTS[job.kind];
        }
      }
    }
  }
```

A job is `queued` for 1.5s, `running` for 4s, then `completed` with a canned result. That is
long enough for the polling UI to actually render each state, which is the point.

It also means **a job only progresses while something is polling it**. If the UI stops asking,
the job still reports the right status the next time anyone looks, because status is derived
rather than stored — but nothing happens in between.

The mock reproduces the backend's job **collapsing**: `enqueueSyncJob` reuses an existing
`queued` job of the same kind instead of adding a second one, and reports `created: 0` so the
UI can say "an equivalent run is already queued". Getting this wrong in the mock hides a real
behaviour, so keep it.

## Async endpoints

Task endpoints answer `202` with an operation envelope and a `Location` header, matching the
backend:

```typescript
  const body = {
    ...buildAsyncResponse(
      operation,
      tracked.id,
      created > 0 ? `${operation} queued (mock)` : 'An equivalent run is already queued.',
      {
        job_ids: jobs.map((job) => job.id),
        tasks: jobs.map((job) => job.kind),
        created,
      },
    ),
    operation_id: tracked.id,
    location: `${apiBaseUrl}/tasks/jobs/${tracked.id}`,
  };

  res.status(202).location(body.location).json(body);
```

`sync_all` queues all five task kinds; `sync_downloads` queues `release_sync` then `export`, the
qBittorrent-hook sequence. The **last** job in a sequence is the one tracked, since its
completion means the whole run is done.

## Adding an endpoint

The mock is the third thing an API change touches, after the spec and the backend:

1. Update `../../../openapi.yaml`.
2. Implement it in the backend and run its contract test.
3. Run `npm run codegen` so `src/lib/api/generated/` has the new types.
4. Add the handler here, typed against the generated types — not against a hand-written shape.
5. `npm run lint` covers `mock-server/` too.

Keep handlers honest about status codes and error bodies. A mock that only ever returns `200`
means the app's error paths are never exercised in development, and `ApiError` handling is the
part most likely to be wrong.
