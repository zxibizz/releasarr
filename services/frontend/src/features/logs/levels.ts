import type { RequestLogLevel } from '@/types';

/**
 * Levels offered as a filter, most severe first.
 *
 * The filter is a threshold, so this reads as "this level and worse". `info` is
 * absent because it is the same as no filter at all.
 */
export const LOG_LEVELS: RequestLogLevel[] = ['error', 'warning'];

export const isLogLevel = (value: unknown): value is RequestLogLevel =>
  LOG_LEVELS.includes(value as RequestLogLevel);
