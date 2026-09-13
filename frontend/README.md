# Releasarr Frontend (v2)

A ground-up rewrite of the Releasarr web UI built on **Vite + React 19 + TypeScript + Mantine**,
talking to the same backend contract described by [`../openapi.yaml`](../openapi.yaml).

## Getting started

```bash
npm install
npm run dev:mock
```

`dev:mock` starts two processes:

| Process | Port | Description                                        |
| ------- | ---- | -------------------------------------------------- |
| `mock`  | 8001 | Express mock API serving the OpenAPI contract       |
| `app`   | 3000 | Vite dev server pointed at `http://localhost:8001/api` |

Open http://localhost:3000 once both are up.

To run the app against a real backend instead, set `VITE_API_URL` and use `npm run dev`.

## Scripts

| Script                | Purpose                                                        |
| --------------------- | -------------------------------------------------------------- |
| `npm run dev`         | Vite dev server only (uses `VITE_API_URL` from `.env`)          |
| `npm run dev:mock`    | Dev server + mock API together                                  |
| `npm run mock:server` | Mock API only                                                   |
| `npm run build`       | Typecheck then production build into `dist/`                    |
| `npm run preview`     | Serve the production build                                      |
| `npm test`            | Run the Vitest suite once                                       |
| `npm run lint`        | ESLint over `src/`, `mock-server/`, and the Vite config         |
| `npm run codegen`     | Regenerate API types from `../openapi.yaml`                     |

## Environment

`.env` holds development defaults:

```
VITE_API_URL=http://localhost:8001/api
VITE_API_KEY=dev-secret
```

`VITE_API_KEY` is sent as the `X-API-Key` header on every request. Use `.env.local`
(git-ignored) for real credentials.

## Architecture

```
src/
  components/      Shared presentational pieces (StatusBadge, EmptyState, Panel,
                   ResponsiveModal, ...)
  features/
    requests/      Request list + detail pages, filtering, localization
    releases/      Release list, card, search, and file mapping
    discover/      Search Sonarr/Radarr/TVDB/TMDB and add requests
    tasks/         System page: scheduled tasks, job history, task logs
    logs/          Request activity logs
  hooks/
    useIsMobile.ts The one place the mobile breakpoint is read in JS
  lib/
    api/client.ts  The single fetch wrapper used by every request
    api/generated/ Types generated from the OpenAPI contract (do not edit)
    i18n.ts        i18next setup
    queryClient.ts TanStack Query defaults
  locales/
    resources.ts   All UI strings, en and ru
  styles/          global.css
  test/utils.tsx   renderWithProviders and viewport helpers
  utils/           Formatters, file helpers, error helpers, status colors
```

A few conventions worth knowing:

- **One HTTP entry point.** Everything goes through `apiRequest` in `lib/api/client.ts`,
  which handles the base URL, auth header, JSON parsing, and `ApiError` normalisation.
  Features declare their endpoints in `features/<name>/api.ts` and their cache keys and
  hooks in `features/<name>/queries.ts`.
- **Types come from the contract.** `src/types.ts` re-exports the generated schema types;
  run `npm run codegen` after `../openapi.yaml` changes rather than hand-editing types.
- **Status colors live in one place.** `utils/status.ts` maps a status to a Mantine color
  and icon, and `StatusBadge` is the only component that renders them.
- **Route loaders warm the cache.** `router.tsx` uses `ensureQueryData` so pages have data
  on first paint; components then read the same query keys.

## Routing

`router.tsx` is a React Router 7 data router. The requests list is bundled eagerly because
it is the landing route; request detail, add, and the system page are `lazy()`. Their
**loaders stay eager** — a lazy route whose loader is also lazy costs a second round trip
before the page can start fetching.

Where a route has a loader it calls `queryClient.ensureQueryData` with the same keys the
components use, so the loader warms the cache and the component reads it rather than
refetching — and `prefetchQuery` for data the page wants but can render without. Routes
whose first paint needs no data (`add`, `system/tasks`) have no loader at all.

## Internationalisation

Every user-visible string comes from `locales/resources.ts`, which holds `en` and `ru` under
a single `translation` namespace. There are no per-feature files; the tree is grouped by
feature inside the one object. `supportedLocales` is derived from its keys, so adding a
locale is adding a key.

Language is resolved from `localStorage` (`releasarr.language`), then the browser, then the
`en` fallback, and persisted on change. `lib/i18n.ts` guards the `localStorage` reads
because they throw in some private browsing modes.

Counts use i18next pluralisation — define `key_one` / `key_other` and let the library pick,
rather than branching in a component. Russian needs `_few` and `_many` too.

Note that **media metadata is localised separately** from the UI: titles and overviews are
localised server-side from TVDB/TMDB translations and arrive on the request, so they follow
`RELEASARR_METADATA_LANGUAGES` rather than the i18next language.

## Mobile

The app is used on phones, so treat narrow viewports as a first-class case rather than a
fallback. The breakpoint is defined once, in `hooks/useIsMobile.ts`, and read two ways:

```typescript
export const MOBILE_BREAKPOINT = '(max-width: 47.99em)';

/**
 * True on phone-sized viewports. Defaults to `false` while the query resolves so
 * the wider layout renders first and never flashes a narrow one on desktop.
 */
export function useIsMobile(): boolean {
  return useMediaQuery(MOBILE_BREAKPOINT, false) ?? false;
}
```

Use `useIsMobile()` for structural differences that CSS cannot express, and Mantine's
responsive props or `styles/global.css` for everything else. The CSS media queries use the
same `47.99em` so both branches switch together — change one and you must change the other.

`ResponsiveModal` already handles the modal-to-full-screen switch; prefer it over a bare
Mantine `Modal`.

## Testing

Vitest with Testing Library and a jsdom environment. `src/test/utils.tsx` renders
components inside the real Mantine, Query, Router, and i18n providers, so tests exercise
the same tree as the app, and offers `setViewportWidth` for the mobile branches.

```bash
npm test
```

Tests mock `apiRequest` rather than the network or the mock server. Conventions and
examples are in [`../docs/testing.md`](../docs/testing.md).

## Docs

| Doc | Covers |
| --- | --- |
| [`docs/file-mapping.md`](docs/file-mapping.md) | The mapping editor: draft state, season-pack routing, bulk actions, save, known gaps |
| [`docs/mock-server.md`](docs/mock-server.md) | The mock API: layout, state, simulated jobs, adding endpoints |

Repo-wide docs are in [`../docs/`](../docs/README.md) —
[`../docs/frontend.md`](../docs/frontend.md) for the patterns to follow when adding code,
[`../AGENTS.md`](../AGENTS.md) for the conventions, and
[`../docs/architecture.md`](../docs/architecture.md) for how the frontend fits the rest.
