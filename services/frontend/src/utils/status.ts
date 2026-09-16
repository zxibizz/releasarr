import type {
  EpisodeStatus,
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
  monitoring: { color: 'indigo', icon: '📡' },
  importing: { color: 'violet', icon: '📥' },
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

/** The one color a "this needs attention" badge uses, wherever it appears. */
export const WARNING_COLOR = 'yellow';

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

export const QUALITY_COLOR: Record<string, string> = {
  '2160p': 'grape',
  '1080p': 'blue',
  '720p': 'teal',
};

/*
  Shared by the episode table and the request card. `pending` is not an
  `EpisodeStatus` — it is the card's word for a missing episode — but both
  readings of a yellow episode belong in the one map.
*/
export const EPISODE_STATUS_COLOR: Record<EpisodeStatus | 'pending', string> = {
  downloaded: 'teal',
  missing: 'yellow',
  pending: 'yellow',
  unaired: 'gray',
};
