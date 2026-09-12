import type { MediaRequestStatus, ReleaseStatus, RequestLogLevel } from '@/types';

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
