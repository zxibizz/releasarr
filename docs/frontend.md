# Frontend guide

Concrete patterns for `services/frontend/`. Paths are relative to `services/frontend/`. See
[`architecture.md`](architecture.md) for how the slices fit together, and
[`../services/frontend/README.md`](../services/frontend/README.md) for the file-mapping
internals.

## Stack

React 19 + Vite + TypeScript, Mantine 9 for UI, TanStack Query 5 for server state, React Router
7 for routing, i18next for strings. npm, `package-lock.json`. Dark mode only —
`forceColorScheme="dark"` in `src/main.tsx`, no toggle.

`@/` aliases `src/` in both `vite.config.ts` and `tsconfig.json`. TypeScript is strict with
`noUnusedLocals` and `noUnusedParameters`; `npm run build` runs `tsc --noEmit` first.

## The HTTP layer

Everything goes through one wrapper, `src/lib/api/client.ts`:

```typescript
apiRequest<T>(path: string, options?: {
  method?: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE';
  body?: unknown;
  query?: Record<string, string | number | boolean | undefined | null>;
  signal?: AbortSignal;
}): Promise<T>
```

It resolves the base URL from `VITE_API_URL` (default `http://localhost:8001/api`), sets
`X-API-Key` from `VITE_API_KEY` (default `dev-secret`), drops empty query values, and normalizes
every failure into an `ApiError` carrying `status` and `details`. An empty body yields
`undefined`, so `apiRequest<void>(…)` works for 204s; a 202 is an ordinary success whose JSON
body is returned.

In the UI, surface errors with `getErrorMessage(error, fallback)` from `src/utils/errors.ts`
rather than reading `error.message` directly.

## Feature slice anatomy

A slice owns its endpoints, its cache keys, and its UI.

```
features/<name>/
  api.ts        Plain object of async functions calling apiRequest
  queries.ts    Key factory, exported query configs, useQuery/useMutation hooks
  keys.ts       Only when a shared key would create an import cycle (see discover/)
  pages/        Route components
  components/   Feature-local UI
```

### api.ts

Export a single object. Encode path params, unwrap response envelopes here, and pass `signal`
through so React Query can cancel:

```typescript
const encode = encodeURIComponent;

export const releasesApi = {
  byRequest: async (requestId: string, signal?: AbortSignal): Promise<Release[]> => {
    const response = await apiRequest<ReleasesResponse>(
      `/requests/${encode(requestId)}/releases`, { signal },
    );
    return response.releases;
  },

  search: (query: string, requestId?: string, signal?: AbortSignal) =>
    apiRequest<ReleaseSearchResponse>('/releases/search', {
      signal, query: { q: query, request_id: requestId },
    }),

  remove: (releaseId: string) =>
    apiRequest<void>(`/releases/${encode(releaseId)}`, { method: 'DELETE' }),
};
```

Encoding is not optional for releases: their ids are Prowlarr GUIDs, commonly forum URLs.

Query param keys are the API's `snake_case`, not camelCase.

### queries.ts

Keys are hierarchical factories, `as const`, so a parent key invalidates its children:

```typescript
export const requestKeys = {
  all: ['requests'] as const,
  lists: () => [...requestKeys.all, 'list'] as const,
  list: (filters?: RequestListFilters) => { /* serialized filters appended */ },
  detail: (id: string) => [...requestKeys.all, 'detail', id] as const,
  episodes: (id: string) => [...requestKeys.all, 'episodes', id] as const,
};
```

Export the query *config* separately from the hook, so route loaders can reuse it:

```typescript
export const releasesByRequestQuery = (requestId: string) => ({
  queryKey: releaseKeys.byRequest(requestId),
  queryFn: ({ signal }: { signal: AbortSignal }) => releasesApi.byRequest(requestId, signal),
});
```

Hooks are named `use` + domain + qualifier: `useReleasesByRequest`, `useReleaseActions`,
`useUpdateFileMappings`, `useRequestSeasons`, `useRemoveRequest`.

Invalidation: prefer the narrowest key you have (`releaseKeys.byRequest(id)` over
`releaseKeys.all`). Cross-feature invalidation is normal and expected — season updates invalidate
`discoverKeys.all`, and saving file mappings invalidates `taskKeys.jobsRoot` because it may have
queued an export. On removal, `removeQueries` the detail key and invalidate the list.

`staleTime` defaults to 30s globally in `src/lib/queryClient.ts`. Override only with a reason —
`useSuggestedFileMappings` sets `staleTime: 0` because a cached mapping suggestion is worse than
none. Polling is the exception and each instance carries its own reason: the job queue while
work is running, Prowlarr's indexer list, and the newest page of the log. The logs page follows
only page 1, because every call makes the server re-read and parse each log file it can reach.

## Types and codegen

```
../../openapi.yaml  →  npm run codegen  →  src/lib/api/generated/types.ts  →  src/types.ts
```

`src/lib/api/generated/types.ts` is **committed but generated** — never hand-edit it. It is in
ESLint's ignore list. `src/types.ts` is the hand-maintained re-export layer; add a line there
when the app needs a new schema:

```typescript
type Schemas = components['schemas'];
export type MediaRequest = Schemas['MediaRequest'];
```

When the contract changes: edit `../../openapi.yaml`, run `npm run codegen`, extend `src/types.ts`,
update the affected `api.ts`/`queries.ts`, and update the mock server. Commit the regenerated
file.

## Routing

`src/router.tsx` defines six routes plus a catch-all, all nested under `AppLayout` with
`RouteErrorBoundary`:

| Path | Component | Loading |
| --- | --- | --- |
| `/` | `RequestsPage` | eager |
| `/request/:id` | `RequestDetailPage` | lazy |
| `/add` | `AddRequestPage` | lazy |
| `/system/tasks` | `TasksPage` | lazy |
| `/system/indexers` | `IndexersPage` | lazy |
| `/system/logs` | `LogsPage` | lazy |
| `*` | `NotFound` | eager |

Loaders warm the cache with `ensureQueryData` so pages paint with data. Note the deliberate
split on the detail route: it blocks on the request, but only *prefetches* releases.

```typescript
const requestDetailLoader = async ({ params }: LoaderFunctionArgs) => {
  await queryClient.ensureQueryData(requestDetailQuery(params.id));
  void queryClient.prefetchQuery(releasesByRequestQuery(params.id));
  return null;
};
```

`src/App.tsx` holds the AppShell: fixed header, `NAV_ITEMS` with per-item `isActive` predicates,
desktop links (`visibleFrom="sm"`) and a mobile `Drawer` (`hiddenFrom="sm"`). It also mounts
`useSyncWatcher()` exactly once — see [`architecture.md`](architecture.md).

A nav item may carry a `badge`, rendered beside its label in both the header and the drawer.
`IndexerAlertBadge` uses this to surface a failing indexer from any page. It calls the same
`useIndexers()` hook as the indexers page, so the shared query key means one poll rather than
two, and it renders nothing on error — an unconfigured Prowlarr must not leave a standing
warning in the header.

Filter state on `/` is URL-synced via `features/requests/useRequestFilters.ts`
(`?type=&status=&sort=&q=`). Keep new filters in the URL rather than component state.

## i18n

`src/locales/resources.ts` holds both locales in one file, keyed by UI area (`nav.*`,
`common.*`, `status.*`, `requestsList.*`, `requestPage.*`, `releaseSearch.*`, `discover.*`,
`tasks.*`). **Every key must exist in both `en` and `ru`.**

Plurals differ by language:

```typescript
// en
episodes_one: '{{count}} episode',
episodes_other: '{{count}} episodes',

// ru
episodes_one: '{{count}} серия',
episodes_few: '{{count}} серии',
episodes_many: '{{count}} серий',
episodes_other: '{{count}} серий',
```

Language choice persists to `localStorage` under `releasarr.language`.

**Metadata localization is a separate concern.** `features/requests/localization.ts` maps the UI
locale to a backend metadata language (`en → eng`, `ru → rus`) and picks
`request.localizations[lang]`. It deliberately does not fall back across languages — a missing
translation shows the *arr app's original title, which is also what the indexer indexed it
under. `useRequestTitles` exposes both titles so release search can switch between them.

## Shared components and utils

| Module | Use it for |
| --- | --- |
| `components/StatusBadge` | Any status display. The only renderer of status colors. |
| `components/ResponsiveModal` | Modals — full-screen on mobile automatically. |
| `components/Panel` | Section containers; drops its border on mobile. |
| `components/EmptyState` | Empty/zero-result states. |
| `components/DataField` | Label/value pairs in mobile card layouts. |
| `utils/status.ts` | `getStatusPresentation` — the single status color/icon table. |
| `utils/formatters.ts` | `formatFileSize`, `formatSpeed`, `formatDate`, `formatDuration`. |
| `utils/files.ts` | `isVideoFile`, `groupFilesByType`, `formatEpisodeCode`. |
| `utils/errors.ts` | `getErrorMessage`, `getErrorInfo`. |

## Mobile

`useIsMobile()` wraps `useMediaQuery('(max-width: 47.99em)')`, kept in sync with the breakpoint
in `src/styles/global.css`. Reach for Mantine's responsive props first (`visibleFrom`,
`hiddenFrom`, `px={{ base: 0, sm: 'md' }}`) and use the hook only for branches props cannot
express — full-screen modals, conditional borders, input vs textarea.

Established mobile patterns: filters and sort controls collapse behind a toggle; tables become
cards; notifications move to top-center; long untrusted strings (release names, file paths) get
`className="break-anywhere"`.

## Styling

Prefer Mantine props for component styling. `src/styles/global.css` is for what props cannot
reach: the page gradient, `font-size: 16px` on mobile inputs (prevents iOS zoom), touch-target
minimums under `@media (pointer: coarse)`, `.safe-area-inline` / `.safe-area-bottom`,
`.break-anywhere`, reduced-motion overrides, and desktop scrollbars. `src/theme.ts` sets the
blue primary, `clamp()`-based responsive headings, and `respectReducedMotion: true`.

## The mock server

`mock-server/` is an Express implementation of the same OpenAPI document, and it is not
optional upkeep — UI work and every screenshot in the README run against it.

| File | Role |
| --- | --- |
| `index.ts` | Express app; routes mount on an `api` router at `/api`; serves `../../openapi.yaml` |
| `store.ts` | `MockStore` — in-memory state, simulated latency, job lifecycle transitions |
| `mockData.ts` | Seed requests, releases, search candidates, mapping suggestions |
| `mockDiscover.ts` | Discover catalogue and root folders |
| `mockLogs.ts` | Log entry generation |

Handlers are thin and delegate to `mockStore`; errors match the contract's `{ code, message }`
shape. Sync jobs auto-advance `queued → running → completed` on timers, which is what makes the
tasks page and `useSyncWatcher` demonstrable without a backend.

One quirk to know when testing by hand: release search matches a plain substring against the
scene-style dotted name, so `The Dark Knight` finds nothing while `The.Dark.Knight` returns
three candidates.

## Checklist for a feature change

1. `../../openapi.yaml` → `npm run codegen` → extend `src/types.ts` if needed.
2. Endpoints into `features/<name>/api.ts`.
3. Keys and hooks into `features/<name>/queries.ts`.
4. Strings into **both** locales in `src/locales/resources.ts`.
5. Mock server routes and store updated.
6. Tests colocated, mocking `@/lib/api/client` — see [`testing.md`](testing.md).
7. `npm run lint && npm test && npm run build`.
