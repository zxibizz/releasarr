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
  components/      Shared presentational pieces (StatusBadge, EmptyState, ...)
  features/
    requests/      Request list + detail pages, filtering, localization
    releases/      Release list, card, search, and file mapping
    logs/          Request activity logs
  lib/
    api/client.ts  The single fetch wrapper used by every request
    api/generated/ Types generated from the OpenAPI contract (do not edit)
    i18n.ts        i18next setup
    queryClient.ts TanStack Query defaults
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

## File mapping

Release files map to requests through a discriminated union (`movie` vs `series`, the
latter carrying season and episode). `useFileMappingForm` keeps an editable flat draft per
file id, tracks which rows are dirty, and serialises drafts back into the union shape on
save. The UI is split into `FileMappingForm` (state + save), `FileMappingToolbar`
(bulk apply, auto-fill, reset), and `FileMappingRow` (a single file's inputs).

## Testing

Vitest with Testing Library and a jsdom environment. `src/test/utils.tsx` renders
components inside the real Mantine, Query, Router, and i18n providers, so tests exercise
the same tree as the app.

```bash
npm test
```
