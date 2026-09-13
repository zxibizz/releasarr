import type { IndexerEventType, IndexerHistoryEntry } from '../src/types';

import { MOCK_INDEXERS } from './mockIndexers';

type HistorySeed = {
  eventType: IndexerEventType;
  successful?: boolean;
  query?: string;
  title?: string;
  source?: string;
  elapsedMs?: number;
  data?: Record<string, string>;
};

/**
 * One round of events, repeated below so pagination has something to page.
 *
 * Covers every event type the UI colours differently, plus a failed query,
 * an event with nothing but its type, and the extra keys Prowlarr attaches for
 * a search but not for a login.
 */
const HISTORY_SEEDS: HistorySeed[] = [
  {
    eventType: 'indexer_query',
    query: 'Severance S02',
    source: 'Sonarr',
    elapsedMs: 412,
    data: { queryResults: '39', host: 'sonarr.example', categories: '5000,5040' },
  },
  {
    eventType: 'release_grabbed',
    title: 'Severance.S02E01.2160p.ATVP.WEB-DL.DDP5.1.H.265',
    source: 'Sonarr',
    data: { downloadClient: 'qBittorrent', publishedDate: '2026-03-01T09:12:00Z' },
  },
  {
    eventType: 'indexer_rss',
    source: 'Prowlarr',
    elapsedMs: 1_840,
    data: { queryResults: '100' },
  },
  {
    eventType: 'indexer_query',
    query: 'Dune Part Two 2024',
    successful: false,
    source: 'Radarr',
    elapsedMs: 30_000,
    data: { host: 'radarr.example', errorMessage: 'Request timed out' },
  },
  {
    eventType: 'indexer_auth',
    source: 'Prowlarr',
    elapsedMs: 96,
  },
  {
    eventType: 'indexer_info',
  },
];

/** Seeded once and reused, so paging and filtering stay stable across calls. */
export const generateMockIndexerHistory = (): IndexerHistoryEntry[] => {
  const now = Date.now();
  const indexers = MOCK_INDEXERS.filter((indexer) => indexer.enabled);

  const entries = Array.from({ length: 8 }).flatMap((_, round) =>
    HISTORY_SEEDS.map((seed, index) => {
      const indexer = indexers[(round + index) % indexers.length];
      const minutesAgo = round * 27 + index * 4;

      return {
        id: round * HISTORY_SEEDS.length + index + 1,
        indexer_id: indexer.id,
        indexer_name: indexer.name,
        occurred_at: new Date(now - minutesAgo * 60_000).toISOString(),
        event_type: seed.eventType,
        successful: seed.successful ?? true,
        query: seed.query ?? null,
        title: seed.title ?? null,
        source: seed.source ?? null,
        elapsed_ms: seed.elapsedMs ?? null,
        data: seed.data ?? {},
      } satisfies IndexerHistoryEntry;
    }),
  );

  entries.sort((a, b) => Date.parse(b.occurred_at) - Date.parse(a.occurred_at));
  return entries;
};
