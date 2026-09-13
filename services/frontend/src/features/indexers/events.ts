import type { IndexerEventType, IndexerLogLevel } from '@/types';

/**
 * Levels offered as a filter, most severe first.
 *
 * The filter is a threshold, so this reads as "this level and worse"; trace is
 * absent because it is the same as no filter at all.
 */
export const INDEXER_LOG_LEVELS: IndexerLogLevel[] = ['fatal', 'error', 'warn', 'info', 'debug'];

export const isIndexerLogLevel = (value: unknown): value is IndexerLogLevel =>
  INDEXER_LOG_LEVELS.includes(value as IndexerLogLevel);

/**
 * Event types offered as a filter, most useful first.
 *
 * `unknown` is deliberately absent: it is what the backend falls back to for an
 * event type a newer Prowlarr invented, so nobody would go looking for it.
 */
export const INDEXER_EVENT_TYPES: IndexerEventType[] = [
  'indexer_query',
  'indexer_rss',
  'release_grabbed',
  'indexer_auth',
  'indexer_info',
];

export const isIndexerEventType = (value: unknown): value is IndexerEventType =>
  INDEXER_EVENT_TYPES.includes(value as IndexerEventType);

/** How long the indexer took, from the millisecond value Prowlarr recorded. */
export const formatElapsed = (elapsedMs: number | null | undefined): string | null => {
  if (elapsedMs == null) return null;
  if (elapsedMs < 1_000) return `${elapsedMs}ms`;
  return `${(elapsedMs / 1_000).toFixed(1)}s`;
};
