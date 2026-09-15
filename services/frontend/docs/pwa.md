# PWA

Releasarr installs to a home screen and opens without a connection. `vite-plugin-pwa` generates
the web manifest and a Workbox service worker as part of `npm run build`; **nothing is generated
in dev** (`devOptions.enabled: false`), so `npm run dev:mock`, `npm test` and the screenshot
harness all run exactly as they did before. Everything the plugin adds is configured in
`vite.config.ts`.

## What is precached

The precache manifest is globbed from `dist/` once the build has finished, so it picks up every
hashed chunk — including the six `lazy()` route chunks — along with `index.html`, `index.css`,
the icons and the manifest. That is why it is generated rather than hand-written: a
hand-written list would go stale the first time a chunk was renamed.

`navigateFallback: 'index.html'` answers any navigation from that shell, so a deep link like
`/system/tasks` opens offline. `navigateFallbackDenylist` keeps `/api` out of the fallback.

## What is never cached

Nothing under `/api` — not precached, and not cached at runtime. There is deliberately **no
`runtimeCaching` block**; adding one is the change most likely to look harmless and be wrong:

- Every response is authenticated, and the refresh cookie is scoped to `/api/auth` and rotates
  exactly once per use (with a 15-second reuse grace). A replayed response reaches the backend
  as a rotated token, which is what token theft looks like.
- The access token lives in memory only, so a cached `200` from a previous session would be
  served to whoever signs in next in that browser.

Requests to `/api` fall straight through to the network. If you need a request to work offline,
that is a product decision, not a caching configuration.

## Updating an installed app

`registerType: 'prompt'`. A new build installs and then waits:

- `src/pwa/UpdatePrompt.tsx` shows a notification with a Reload button that calls
  `updateServiceWorker(true)`, applying the new build immediately.
- Ignoring the prompt loses nothing: the waiting worker takes over on the next cold start once
  the tab is closed, because `skipWaiting` and `clientsClaim` are both off.

A client-side route change is not a navigation as far as the browser is concerned, so the
component also calls `registration.update()` when the tab becomes visible and once an hour. A
tab left open across a deploy would otherwise keep running the build it was opened with.

## Offline behaviour

There is no offline data. What the service worker buys is the shell plus an honest explanation:

| Piece                                        | Job                                                                                                                                                                                                                                |
| -------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/hooks/useOnlineStatus.ts`               | `navigator.onLine` as a subscribable value                                                                                                                                                                                         |
| `src/components/OfflineNotice.tsx`           | One non-dismissible notification while offline — every poll in the app is a `refetchInterval`, so a page that has stopped updating says why                                                                                        |
| `src/components/OfflineState.tsx`            | The full-page state, used by both of the below                                                                                                                                                                                     |
| `RequireAuth`                                | Offline and anonymous, shows that state instead of redirecting to `/login` — the refresh call never left the machine, so "no session" cannot be distinguished from "could not ask", and a sign-in form that cannot submit is worse |
| `RouteErrorBoundary`                         | `isNetworkError(error)` (an `ApiError` whose cause is a `TypeError`, i.e. `fetch` never reached the server) renders the same state rather than "Something went wrong"                                                              |
| `prefetchWhenOnline` in `lib/queryClient.ts` | Route loaders skip their prefetch when offline                                                                                                                                                                                     |

That last one is the subtle one. React Query **pauses** a query instead of failing it while it
believes there is no connection, so `ensureQueryData` can hang indefinitely. A loader awaiting a
paused query leaves the router in its initial loading state, and the app renders the hydration
fallback forever — the offline screen is never reached, because it lives below the loader that is
stuck. Any new loader must therefore go through `prefetchWhenOnline`, which reads
`navigator.onLine` directly: React Query's online manager only learns the state from a browser
event, so on a cold start it can still report online while the browser does not.

## Icons

`public/favicon.svg` is the source of truth — full-bleed, with the glyph inside the central 80%
so it survives a launcher masking it to a circle. The rest are generated and committed:

```bash
npm run pwa:assets
```

`pwa-assets.config.ts` overrides the `minimal-2023` preset's padding colour, which otherwise
defaults to white and shows as a pale ring around a dark icon. **A normal build never runs the
generator** — it reads the committed PNGs — so changing the artwork is a deliberate two-step:
edit the SVG, regenerate, commit both.

## HTTPS

A service worker only registers in a secure context: `https://`, or `http://localhost`. The
production image serves plain HTTP on port 80, so installation and offline support only work
behind a TLS reverse proxy (or from `localhost` itself). On a plain `http://<lan-ip>:8050` the app
still works — the manifest and the icons are simply inert, because the browser refuses to run the
worker.

## Checking a change

After `npm run build`, all of these should hold:

1. `dist/sw.js`, `dist/workbox-*.js` and `dist/manifest.webmanifest` exist, and the build log
   reports the precache entry count.
2. The precache list contains a `RequestDetailPage-*.js` entry and **no** `/api` entry.
3. `npm run preview`, then in DevTools: Application → Manifest has no errors; Service Workers
   shows one activated worker; a reload shows assets served from the service worker.
4. Offline (DevTools → Network → Offline) and hard-reloading a deep link boots the shell and
   shows the offline state, with the URL unchanged — not a redirect to `/login`, and not a
   spinner that never resolves.
