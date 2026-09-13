import type { Page } from 'playwright-core';

import { scrollTextIntoView, settle, waitForEnabled } from './harness';

export interface Shot {
  /** Output filename, without the extension. */
  name: string;
  /** What the image is meant to show, printed by `--list`. */
  description: string;
  /** Route to open, relative to the app root. */
  route: string;
  /** Overrides the default viewport for shots that frame better shorter or taller. */
  viewport?: { width: number; height: number };
  /**
   * Drives the UI into the state worth photographing. The page has already
   * navigated and settled; `settle` again after anything that refetches.
   */
  prepare?: (page: Page) => Promise<void>;
}

/**
 * Each shot must stand on its own so a single image can be re-captured without
 * the others. Where two images show steps of one flow, the later one repeats
 * the earlier steps rather than depending on a leftover page.
 */
export const shots: Shot[] = [
  {
    name: 'requests',
    description: 'Requests dashboard with the seeded mixture of statuses',
    route: '/',
  },
  {
    name: 'request-detail',
    description: 'Request detail for a movie mid-download',
    route: '/request/2',
  },
  {
    name: 'release-search',
    description: 'Indexer search results for a manual search',
    route: '/request/1',
    prepare: async (page) => {
      await page.getByText('Manual Search', { exact: true }).first().click();
      // The mock indexer substring-matches the scene-style dotted name, so a
      // human-readable "The Dark Knight" returns nothing.
      await page.getByRole('searchbox').first().fill('The.Dark.Knight');
      await page.getByRole('button', { name: 'Search', exact: true }).first().click();
      await page.getByText('Search Results').first().waitFor();
      await settle(page);
      await scrollTextIntoView(page, 'Search Results');
    },
  },
  {
    name: 'file-mapping',
    description: 'Mapping editor for a season pack',
    route: '/request/5',
    prepare: async (page) => {
      // Several cards carry a Files button; the season pack is the last one.
      await page
        .getByRole('button', { name: /^Files$/i })
        .last()
        .click();
      await page.getByRole('tab', { name: /Mapping/i }).click();
      // The toolbar unlocks only once the suggestions have arrived and filled
      // the rows, which is the state the image is meant to show.
      await waitForEnabled(page.getByRole('button', { name: /Use suggested mapping/i }));
      await settle(page);
    },
  },
  {
    name: 'discover-seasons',
    description: 'Season picker with the state Sonarr already holds merged in',
    route: '/add',
    // The picker is short; the full-height viewport would be mostly empty.
    viewport: { width: 1500, height: 620 },
    prepare: async (page) => {
      await searchDiscover(page);
      await page.getByRole('button', { name: /Choose seasons/i }).click();
      await settle(page);
    },
  },
  {
    name: 'tasks',
    description: 'System page with a task run in flight',
    route: '/system/tasks',
    prepare: async (page) => {
      await page.getByRole('button', { name: /Run all tasks/i }).click();
      // The mock holds each job queued for 1.5s and running for 4s, so the
      // shot has to land in that window. Waiting for the badge gets us in;
      // allowing spinners keeps us there, and nothing below may block.
      await page.getByText('Running').first().waitFor();
      await settle(page, { allowSpinners: true });
    },
  },
];

/** The search that has to happen before the season picker can be opened. */
async function searchDiscover(page: Page): Promise<void> {
  await page.getByPlaceholder(/Search movies and series/i).fill('Breaking Bad');
  await page.getByRole('button', { name: 'Search', exact: true }).first().click();
  await page.getByRole('button', { name: /Choose seasons/i }).first().waitFor();
  await settle(page);
}
