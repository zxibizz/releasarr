import { useQuery } from '@tanstack/react-query';

import { logsApi } from '@/features/logs/api';
import type { LogComponent, LogService, RequestLogLevel, SyncJobKind } from '@/types';

export const LOGS_PAGE_SIZE = 25;

/**
 * Interval for the log page's follow mode. Every call re-reads and parses each
 * reachable log file on the server, so this runs well clear of the task polling
 * intervals and only while the newest page is on screen.
 */
export const LOGS_POLL_INTERVAL_MS = 10_000;

export const logKeys = {
  all: ['logs'] as const,
  byRequest: (requestId: string) => [...logKeys.all, 'by-request', requestId] as const,
  list: (filters: {
    page: number;
    service?: LogService;
    component?: LogComponent;
    task?: SyncJobKind;
    minLevel?: RequestLogLevel;
  }) => [...logKeys.all, 'list', filters] as const,
};

/**
 * Activity log for a single request. Only fetched while the modal is open, since
 * the backend parses the whole log file on every call.
 */
export function useRequestLogs(requestId: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: logKeys.byRequest(requestId ?? ''),
    queryFn: ({ signal }: { signal: AbortSignal }) => logsApi.byRequest(requestId ?? '', signal),
    enabled: Boolean(requestId) && enabled,
  });
}

/**
 * A page of application logs, optionally narrowed to a process, a component, or a
 * severity.
 *
 * The newest page refetches on an interval so the view follows the log as it is
 * written; a page further back is a deliberate, static read. Every call makes the
 * server re-parse each log file it can reach, which is what the interval is sized
 * against.
 */
export function useLogs({
  page,
  service,
  component,
  minLevel,
}: {
  page: number;
  service?: LogService;
  component?: LogComponent;
  minLevel?: RequestLogLevel;
}) {
  return useQuery({
    queryKey: logKeys.list({ page, service, component, minLevel }),
    queryFn: ({ signal }) =>
      logsApi.list({ page, perPage: LOGS_PAGE_SIZE, service, component, minLevel }, signal),
    placeholderData: (previous) => previous,
    refetchInterval: page === 1 ? LOGS_POLL_INTERVAL_MS : false,
  });
}
