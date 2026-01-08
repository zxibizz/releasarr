# Releasarr Frontend

A React + TypeScript client for managing media requests and releases in Releasarr. The UI is built with Chakra UI and centralises request/release state in shared context providers so every screen stays in sync.

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
2. Start the dev server against a running API (defaults to `http://localhost:8001/api`):
   ```bash
   npm start
   ```
3. Visit [http://localhost:3000](http://localhost:3000) in your browser.

### Working with the mock API
When the backend is unavailable, launch the mock workflow:
```bash
npm run dev:mock
```
This spins up the Express/MSW mock service on `http://localhost:8001/api` and the React dev server concurrently. The mock honours the OpenAPI contract, including mutation endpoints, so refresh, manual search, and file mapping features behave as they would against the real API.

## Scripts
- `npm start` – CRA dev server
- `npm run dev:mock` – dev server + OpenAPI-driven mock API
- `npm run build` – production build

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
- `RequestsProvider` and `ReleasesProvider` expose cached collections, fetch helpers, and imperative actions to every component via context.
- `services/api.ts` wraps the REST API with structured errors, timeout/abort support, and convenience helpers used by hooks.
- Release search, manual actions, and logs share the same data caches so updates propagate instantly across cards, modals, and detail views.

## Environment Variables
- `REACT_APP_API_URL` – base URL for the Releasarr API or mock server (defaults to `http://localhost:8001/api`).
