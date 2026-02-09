# Releasarr Frontend

A Vite-powered React + TypeScript client for managing media requests and releases in Releasarr. The UI is built with Chakra UI and centralises request/release state in shared context providers so every screen stays in sync.

## Highlights

- Requests dashboard with filtering by media type and lifecycle state
- Request detail view with release status, manual search, logs, and file mapping modals
- Toast-driven feedback for long-running actions (refresh, manual search, mapping updates)
- Defensive API layer with typed error objects, abort support, and mock server parity

## Stack

- React 18 with functional components and hooks
- Chakra UI design system and motion primitives
- React Router 6 layout routing (navigation shell + nested pages)

## Getting Started

1. Install dependencies:
   ```bash
   npm install
   ```
2. Start the Vite dev server against a running API (defaults to `http://localhost:8001/api`):
   ```bash
   npm run dev
   ```
3. Visit [http://localhost:3000](http://localhost:3000) in your browser.

### Working with the mock API

When the backend is unavailable, launch the mock workflow:

```bash
npm run dev:mock
```

This spins up the Express/MSW mock service on `http://localhost:8001/api` and the Vite dev server concurrently. The mock honours the OpenAPI contract, including mutation endpoints, so refresh, manual search, and file mapping features behave as they would against the real API.

## Scripts

- `npm run dev` – Vite dev server
- `npm run dev:mock` – mock server + Vite dev server
- `npm run build` – type-check and production build
- `npm run preview` – preview the production build locally
- `npm run lint` – ESLint (type-aware) pass with React/Chakra rules
- `npm run format` – Prettier formatting for the entire workspace
- `npm run codegen` – regenerate Zod schemas and typed clients from `openapi.yaml`

## Project Structure

```
src/
├── App.tsx
├── components/
│   ├── RequestsList.tsx
│   ├── RequestPage.tsx
│   ├── ReleaseSearch.tsx
│   ├── ReleaseFilesModal.tsx
│   └── NotFound.tsx
├── hooks/
│   ├── useRequests.tsx
│   └── useReleases.tsx
├── services/
│   ├── api.ts
│   └── requestLogs.ts
├── theme.ts
└── utils/
    ├── formatters.ts
    └── releaseHelpers.ts
```

## Architecture Notes

- Absolute imports are available via the `@/` alias (configured in `tsconfig.json` and `vite.config.ts`), keeping feature modules decoupled from relative path chains.
- `npm run codegen` regenerates the `src/generated/releasarr.ts` client and schemas from `openapi.yaml`; `src/types/index.ts` re-exports these schemas and inferred types for the rest of the app.
- `RequestsProvider` and `ReleasesProvider` expose cached collections, fetch helpers, and imperative actions to every component via context.
- `services/api.ts` wraps the REST API with structured errors, timeout/abort support, and convenience helpers used by hooks.
- Release search, manual actions, and logs share the same data caches so updates propagate instantly across cards, modals, and detail views.

## Environment Variables

- `VITE_API_URL` – base URL for the Releasarr API or mock server (defaults to `http://localhost:8001/api`).
