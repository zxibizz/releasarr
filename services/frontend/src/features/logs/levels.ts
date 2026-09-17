import type { RequestLogLevel } from '@/types';

/**
 * Levels offered as a filter, most severe first.
 *
 * The filter is a threshold, so this reads as "this level and worse". `debug` is
 * absent because it is the same as no filter at all; `info` is how the request
 * lines the API logs per request are kept out of the view.
 */
export const LOG_LEVELS: RequestLogLevel[] = ['error', 'warning', 'info'];

export const isLogLevel = (value: unknown): value is RequestLogLevel =>
  LOG_LEVELS.includes(value as RequestLogLevel);
