import { notifications } from '@mantine/notifications';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';

import { indexersApi } from '@/features/indexers/api';
import type { Indexer, IndexerTestResult } from '@/types';
import { getErrorMessage } from '@/utils/errors';

export const indexerKeys = {
  all: ['indexers'] as const,
  list: () => ['indexers', 'list'] as const,
};

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
