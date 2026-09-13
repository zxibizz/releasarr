import { notifications } from '@mantine/notifications';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';

import { indexersApi } from '@/features/indexers/api';
import type { Indexer, IndexerEventType, IndexerLogLevel, IndexerTestResult } from '@/types';
import { getErrorMessage } from '@/utils/errors';

export interface IndexerHistoryFilters {
  page: number;
  indexerId?: number;
  eventType?: IndexerEventType;
}

export interface IndexerLogFilters {
  page: number;
  minLevel?: IndexerLogLevel;
}

export const indexerKeys = {
  all: ['indexers'] as const,
  list: () => ['indexers', 'list'] as const,
  history: (filters: IndexerHistoryFilters) => ['indexers', 'history', filters] as const,
  logs: (filters: IndexerLogFilters) => ['indexers', 'logs', filters] as const,
};

export const HISTORY_PAGE_SIZE = 25;

/**
 * Prowlarr lifts its own back-off on a timer, so the list goes stale on its own
 * even when nothing here changes it.
 */
const POLL_INTERVAL_MS = 60_000;

/** Health states worth interrupting the reader over. */
export const isIndexerUnhealthy = (indexer: Indexer) =>
  indexer.health === 'blocked' || indexer.health === 'degraded';

/**
 * The indexer list.
 *
 * Both the page and the nav badge call this, and the shared key means they
 * share one request rather than polling Prowlarr twice.
 */
export function useIndexers() {
  return useQuery({
    queryKey: indexerKeys.list(),
    queryFn: ({ signal }) => indexersApi.list(signal),
    refetchInterval: POLL_INTERVAL_MS,
  });
}

/**
 * A page of Prowlarr's own log, the one its UI shows as System → Events.
 *
 * Only fetched while its tab is showing: every call reaches Prowlarr, and
 * neither this nor the history is something releasarr changes. The previous page
 * stays on screen while the next loads, so paging does not blank the table.
 */
export function useIndexerLogs(filters: IndexerLogFilters, enabled: boolean) {
  return useQuery({
    queryKey: indexerKeys.logs(filters),
    queryFn: ({ signal }) =>
      indexersApi.logs(
        { page: filters.page, perPage: HISTORY_PAGE_SIZE, minLevel: filters.minLevel },
        signal,
      ),
    enabled,
    placeholderData: (previous) => previous,
  });
}

/** A page of Prowlarr's indexer history. Fetched only while its tab is showing. */
export function useIndexerHistory(filters: IndexerHistoryFilters, enabled: boolean) {
  return useQuery({
    queryKey: indexerKeys.history(filters),
    queryFn: ({ signal }) =>
      indexersApi.history(
        {
          page: filters.page,
          perPage: HISTORY_PAGE_SIZE,
          indexerId: filters.indexerId,
          eventType: filters.eventType,
        },
        signal,
      ),
    enabled,
    placeholderData: (previous) => previous,
  });
}

function useTestNotifications() {
  const { t } = useTranslation();

  return {
    onResult: (results: IndexerTestResult[]) => {
      const failed = results.filter((result) => !result.success);
      if (failed.length === 0) {
        notifications.show({
          message: t('indexers.toasts.passed', { count: results.length }),
          color: 'teal',
        });
        return;
      }

      notifications.show({
        title: t('indexers.toasts.failedTitle', { count: failed.length }),
        message: failed
          .map((result) => [result.name, ...result.errors].filter(Boolean).join(': '))
          .join('\n'),
        color: 'red',
      });
    },
    onError: (error: unknown) => {
      notifications.show({
        title: t('indexers.toasts.errorTitle'),
        message: getErrorMessage(error, t('indexers.toasts.errorFallback')),
        color: 'red',
      });
    },
  };
}

export function useTestIndexer() {
  const queryClient = useQueryClient();
  const notify = useTestNotifications();

  return useMutation({
    mutationFn: (indexerId: number) => indexersApi.test(indexerId),
    onSuccess: (result) => notify.onResult([result]),
    onError: notify.onError,
    // A passing test clears Prowlarr's back-off, so the health it reported is
    // out of date either way.
    onSettled: () => queryClient.invalidateQueries({ queryKey: indexerKeys.all }),
  });
}

export function useTestAllIndexers() {
  const queryClient = useQueryClient();
  const notify = useTestNotifications();

  return useMutation({
    mutationFn: indexersApi.testAll,
    onSuccess: notify.onResult,
    onError: notify.onError,
    onSettled: () => queryClient.invalidateQueries({ queryKey: indexerKeys.all }),
  });
}
