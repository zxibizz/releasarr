import { notifications } from '@mantine/notifications';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';

import { discoverApi } from '@/features/discover/api';
import { discoverKeys } from '@/features/discover/keys';
import { requestKeys } from '@/features/requests/queries';
import type { AddRequestPayload, MediaType } from '@/types';
import { getErrorMessage } from '@/utils/errors';

export { discoverKeys };

/**
 * Searching hits TVDB/TMDB and both *arr apps, so results are held longer than
 * the default and only refetched when the term itself changes.
 *
 * The titles and overviews come back in the UI's own language where the provider
 * has a translation, which puts the language in the key: switching it has to
 * fetch a new set of results.
 */
export function useMediaSearch(query: string) {
  const { i18n } = useTranslation();
  const trimmed = query.trim();
  const language = i18n.language;

  return useQuery({
    queryKey: discoverKeys.search(trimmed, language),
    queryFn: ({ signal }) => discoverApi.search(trimmed, language, signal),
    enabled: trimmed.length > 0,
    staleTime: 5 * 60 * 1000,
  });
}

export function useSeriesSeasons(tvdbId: number | undefined) {
  return useQuery({
    queryKey: discoverKeys.seasons(tvdbId ?? 0),
    queryFn: ({ signal }) => discoverApi.seriesSeasons(tvdbId ?? 0, signal),
    enabled: Boolean(tvdbId),
  });
}

export function useRootFolders(type: MediaType) {
  return useQuery({
    queryKey: discoverKeys.rootFolders(type),
    queryFn: ({ signal }) => discoverApi.rootFolders(type, signal),
    staleTime: 5 * 60 * 1000,
  });
}

export function useAddRequest() {
  const queryClient = useQueryClient();
  const { t } = useTranslation();

  return useMutation({
    mutationFn: (payload: AddRequestPayload) => discoverApi.addRequest(payload),
    onSuccess: (response) => {
      notifications.show({
        // A series whose every season is already covered is added for its
        // future-seasons setting alone, and comes back with no request to
        // announce. "Added 0 requests" would read as a failure.
        message:
          response.requests.length === 0
            ? t('discover.monitoringUpdated', { defaultValue: 'Monitoring updated' })
            : t('discover.added', {
                count: response.requests.length,
                defaultValue: 'Added {{count}} request',
                defaultValue_other: 'Added {{count}} requests',
              }),
        color: 'teal',
      });
      // The added media now has requests, so both the request list and the
      // search results that report their state are out of date.
      void queryClient.invalidateQueries({ queryKey: requestKeys.all });
      void queryClient.invalidateQueries({ queryKey: discoverKeys.all });
    },
    onError: (error: unknown) => {
      notifications.show({
        title: t('discover.addFailed', { defaultValue: 'Failed to add request' }),
        message: getErrorMessage(error, ''),
        color: 'red',
      });
    },
  });
}
