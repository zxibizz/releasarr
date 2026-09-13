import type { Indexer } from '../src/types';

const hoursFromNow = (hours: number) => new Date(Date.now() + hours * 3_600_000).toISOString();

/**
 * Seed indexers covering all four health states, since the page exists to tell
 * them apart and the badge only appears for two of them.
 *
 * `health` is derived by the backend rather than reported by Prowlarr, so these
 * are pre-derived to match what the real endpoint would return for the
 * timestamps below.
 */
export const MOCK_INDEXERS: Indexer[] = [
  {
    id: 1,
    name: 'Anthelion',
    health: 'healthy',
    enabled: true,
    protocol: 'torrent',
    privacy: 'private',
    priority: 25,
    supports_search: true,
    supports_rss: true,
    indexer_urls: ['https://anthelion.example/'],
    disabled_till: null,
    most_recent_failure: null,
    initial_failure: null,
  },
  {
    id: 2,
    name: 'BeyondHD',
    health: 'blocked',
    enabled: true,
    protocol: 'torrent',
    privacy: 'private',
    priority: 10,
    supports_search: true,
    supports_rss: true,
    indexer_urls: ['https://beyondhd.example/'],
    disabled_till: hoursFromNow(4),
    most_recent_failure: hoursFromNow(-1),
    initial_failure: hoursFromNow(-9),
  },
  {
    id: 3,
    name: 'Nyaa',
    health: 'degraded',
    enabled: true,
    protocol: 'torrent',
    privacy: 'public',
    priority: 40,
    supports_search: true,
    supports_rss: false,
    indexer_urls: ['https://nyaa.example/'],
    disabled_till: null,
    most_recent_failure: hoursFromNow(-3),
    initial_failure: hoursFromNow(-4),
  },
  {
    id: 4,
    name: 'RuTracker',
    health: 'disabled',
    enabled: false,
    protocol: 'torrent',
    privacy: 'semiPrivate',
    priority: 50,
    supports_search: true,
    supports_rss: true,
    indexer_urls: ['https://rutracker.example/'],
    disabled_till: null,
    most_recent_failure: null,
    initial_failure: null,
  },
];

/** Indexers the mock test run reports as still broken, by id. */
export const MOCK_FAILING_INDEXER_IDS = new Set([3]);
