import type { LogService } from '@/types';

/**
 * The processes that share one log file, in the order the tabs present them.
 *
 * The API is first because its records are what a request produces; the
 * scheduler's are what that request went on to have done.
 */
export const LOG_SERVICES: LogService[] = ['api', 'scheduler'];

export const DEFAULT_LOG_SERVICE: LogService = 'api';

export const isLogService = (value: unknown): value is LogService =>
  LOG_SERVICES.includes(value as LogService);
