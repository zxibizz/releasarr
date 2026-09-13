import type {
  IndexerEventType,
  IndexerLogLevel,
  MediaRequestStatus,
  ReleaseStatus,
  RequestLogLevel,
} from '@/types';

export type StatusPresentation = {
  /** Mantine theme color used for badges and accents. */
  color: string;
  icon: string;
};

const STATUS_PRESENTATION = {
  pending: { color: 'yellow', icon: '⏳' },
  searching: { color: 'grape', icon: '🔍' },
  downloading: { color: 'blue', icon: '⬇️' },
  seeding: { color: 'cyan', icon: '🌱' },
  completed: { color: 'teal', icon: '✅' },
  failed: { color: 'red', icon: '❌' },
  queued: { color: 'gray', icon: '🕒' },
  running: { color: 'blue', icon: '⚙️' },
  healthy: { color: 'teal', icon: '✅' },
  degraded: { color: 'yellow', icon: '⚠️' },
  blocked: { color: 'red', icon: '⛔' },
  disabled: { color: 'gray', icon: '🚫' },
} as const satisfies Record<string, StatusPresentation>;

const UNKNOWN_STATUS: StatusPresentation = { color: 'gray', icon: '❓' };

export const getStatusPresentation = (
  status: MediaRequestStatus | ReleaseStatus | string,
): StatusPresentation =>
  STATUS_PRESENTATION[status as keyof typeof STATUS_PRESENTATION] ?? UNKNOWN_STATUS;

export const LOG_LEVEL_COLOR: Record<RequestLogLevel, string> = {
  info: 'blue',
  warning: 'yellow',
  error: 'red',
};

const INDEXER_EVENT_COLOR: Record<IndexerEventType, string> = {
  indexer_query: 'blue',
  indexer_rss: 'cyan',
  indexer_auth: 'grape',
  indexer_info: 'gray',
  release_grabbed: 'teal',
  unknown: 'gray',
};

/** A failed event reads as a failure first and as its kind second. */
export const getIndexerEventColor = (eventType: IndexerEventType, successful: boolean): string =>
  successful ? (INDEXER_EVENT_COLOR[eventType] ?? 'gray') : 'red';

export const INDEXER_LOG_LEVEL_COLOR: Record<IndexerLogLevel, string> = {
  trace: 'gray',
  debug: 'gray',
  info: 'blue',
  warn: 'yellow',
  error: 'red',
  fatal: 'red',
};
