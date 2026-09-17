import type { LogService } from '@/types';

/**
 * The processes that write the log files the page merges.
 *
 * The API is first because its records are what a request produces; the
 * scheduler's are what that request went on to have done.
 */
export const LOG_SERVICES: LogService[] = ['api', 'scheduler'];

export const isLogService = (value: unknown): value is LogService =>
  LOG_SERVICES.includes(value as LogService);
