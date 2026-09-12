import type { SyncJobKind } from '@/types';
import { formatDuration } from '@/utils/formatters';

/** Task order used by every list in the UI, matching the backend's run order. */
export const TASK_KINDS: SyncJobKind[] = ['sonarr_sync', 'release_sync', 'export', 'regrab'];

/** Narrows values that arrive untyped, such as a log record's bound fields. */
export const isTaskKind = (value: unknown): value is SyncJobKind =>
  TASK_KINDS.includes(value as SyncJobKind);

/** How long a task run took, from the millisecond value the API reports. */
export const formatRunDuration = (durationMs: number | null | undefined): string | null => {
  if (durationMs == null) return null;
  if (durationMs < 1_000) return `${durationMs}ms`;
  return formatDuration(durationMs / 1_000);
};

export const formatInterval = (seconds: number): string => formatDuration(seconds);

/**
 * Time until (or since) a timestamp, in the reader's locale.
 *
 * Used for the next and last execution columns, where the offset matters more
 * than the wall-clock time; the exact timestamp is shown on hover.
 */
export const formatRelativeTime = (value: string, locale: string, now = Date.now()): string => {
  const target = new Date(value).getTime();
  if (Number.isNaN(target)) return value;

  const seconds = Math.round((target - now) / 1000);
  const formatter = new Intl.RelativeTimeFormat(locale, { numeric: 'auto' });

  const units: [Intl.RelativeTimeFormatUnit, number][] = [
    ['day', 86_400],
    ['hour', 3_600],
    ['minute', 60],
  ];

  for (const [unit, secondsPerUnit] of units) {
    if (Math.abs(seconds) >= secondsPerUnit) {
      return formatter.format(Math.round(seconds / secondsPerUnit), unit);
    }
  }

  return formatter.format(seconds, 'second');
};
