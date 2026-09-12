import type { RequestLogEntry } from '@/types';

/**
 * Renders a record's bound fields as `key=value` pairs.
 *
 * `hiddenKeys` drops fields the surrounding UI already conveys, such as the
 * identifier the view is filtered by.
 */
export const formatLogContext = (
  metadata: RequestLogEntry['metadata'],
  hiddenKeys: Iterable<string> = [],
): string | null => {
  if (!metadata) {
    return null;
  }

  const hidden = new Set(hiddenKeys);
  const entries = Object.entries(metadata).filter(
    ([key, value]) => !hidden.has(key) && value !== null && value !== '',
  );

  if (entries.length === 0) {
    return null;
  }

  return entries.map(([key, value]) => `${key}=${String(value)}`).join('  ');
};
