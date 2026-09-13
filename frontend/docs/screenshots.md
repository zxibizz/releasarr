# Screenshots

`scripts/screenshots/` captures the images the root [`README.md`](../../README.md) embeds, by
driving the real UI against the [mock API](mock-server.md). Commands are in the
[frontend README](../README.md#screenshots).

```
scripts/screenshots/
  shots.ts      What to photograph, one entry per image
  harness.ts    Servers, browser, and the waiting helpers
  capture.ts    CLI and the capture loop
```

Only `shots.ts` should need editing to add an image.

## Adding a shot

```typescript
{
  name: 'release-search',
  description: 'Indexer search results for a manual search',
  route: '/request/1',
  prepare: async (page) => {
    await page.getByText('Manual Search', { exact: true }).first().click();
    await page.getByRole('searchbox').first().fill('The.Dark.Knight');
    await page.getByRole('button', { name: 'Search', exact: true }).first().click();
    await page.getByText('Search Results').first().waitFor();
    await settle(page);
    await scrollTextIntoView(page, 'Search Results');
  },
}
```

`name` is the output filename. The page is navigated and settled before `prepare` runs, and
screenshotted after it returns. Add `viewport` where the default 1500×980 frames badly — the
season picker is short enough that the full height would be mostly empty background.

Each shot gets a **fresh browser context**, so viewport overrides and anything a `prepare`
leaves behind cannot leak into the next image. It also means a shot may not depend on an
earlier one having run: `discover-seasons` repeats the search that `discover` would have done
rather than inheriting a page. That is what makes `npm run screenshots -- discover-seasons`
work on its own.

Every shot the tool defines is a shot the README embeds. Capturing an image nothing links to
just puts an unexplained binary in git.

## Waiting

This is the whole difficulty, and the reason the tool exists. The script this replaced used
about 20 seconds of `waitForTimeout` calls, which was both slow and unreliable. Three rules:

**Wait for the thing you are photographing, not for time to pass.** The mapping editor's
toolbar is disabled until the suggestions query lands and fills the rows. Waiting for that
button to enable is precise; `waitForTimeout(1800)` was a guess that silently produced an
image of empty request selects when the machine was busy.

```typescript
await waitForEnabled(page.getByRole('button', { name: /Use suggested mapping/i }));
```

**`networkidle` is not enough.** React Query fires its requests well after the load event, so
a page can be "idle" while the data the shot needs is still in flight. `settle()` waits for
network quiet, for spinners to clear, for fonts, and for a painted frame — but a semantic wait
still has to come first.

**Spinners are sometimes the subject.** `settle()` waits for `.mantine-Loader-root` to
disappear, which on the tasks page means waiting for the jobs to finish — the opposite of what
that image wants. Pass `settle(page, { allowSpinners: true })` when the busy state is the
point.

The mock advances jobs on wall-clock time: queued for 1.5s, running for 4s (see
[`mock-server.md`](mock-server.md)). The tasks shot has to land in that window, so nothing
between the click and the capture may block.

## Stillness

`applyStillness` injects a stylesheet after navigation that zeroes animations and transitions,
hides the text caret, and hides notifications entirely.

All three are flakiness fixes. Mantine's transitions mean an otherwise-identical page differs
between runs; a blinking caret in a filled search box appears in roughly half of captures; and
toasts arrive on their own schedule, so dismissing them by clicking races whatever fires next
— which is how a "Sync finished" toast ended up over the tasks page header. No shot wants a
toast, so they are removed rather than timed.

This is injected after `goto` rather than as an init script. An init script runs against an
empty document and has to defer to `DOMContentLoaded`, which did not reliably land the
stylesheet. A shot navigates once and then stays inside the SPA, so injecting after navigation
is enough.

## Browsers

The dependency is `playwright-core`, not `playwright`, because the full package downloads a
browser on every `npm install` — a steep price for a tool that runs when the README needs new
images. So the tool finds a browser instead of shipping one, in order:

1. `RELEASARR_CHROMIUM`, if set.
2. Playwright's pinned Chromium, from `npx playwright install chromium`.
3. A locally installed Google Chrome.

If none resolve it prints those options rather than a Playwright stack trace. Using system
Chrome means the browser version is not pinned, which is fine for README images and would not
be if these were pixel-comparison tests.
