import { notifications } from '@mantine/notifications';
import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';

import { discoverKeys } from '@/features/discover/keys';
import { requestsApi, type RequestListFilters } from '@/features/requests/api';
import type { RequestsResponse, UpdateSeasonsPayload } from '@/types';
import { getErrorMessage } from '@/utils/errors';

const serializeFilters = (filters?: RequestListFilters) =>
  Object.entries(filters ?? {})
    .filter(([, value]) => value !== undefined && value !== null)
    .sort(([a], [b]) => a.localeCompare(b));

export const requestKeys = {
  all: ['requests'] as const,
  lists: () => [...requestKeys.all, 'list'] as const,
  list: (filters?: RequestListFilters) => {
    const serialized = serializeFilters(filters);
    return serialized.length === 0
      ? requestKeys.lists()
      : ([...requestKeys.lists(), serialized] as const);
  },
  detail: (id: string) => [...requestKeys.all, 'detail', id] as const,
  episodes: (id: string) => [...requestKeys.all, 'episodes', id] as const,
  seasons: (id: string) => [...requestKeys.all, 'seasons', id] as const,
};

type RequestsListQueryFilters = Omit<RequestListFilters, 'page' | 'perPage'>;

/**
 * The API does the filtering now, so the page size is the contract's maximum:
 * a filter change is one request, not one per page of twenty.
 */
export const REQUESTS_PAGE_SIZE = 100;

/** The URL defaults made explicit; the list route loader prefetches this key. */
export const DEFAULT_REQUESTS_LIST_FILTERS: RequestsListQueryFilters = {
  status: 'active',
  sort: 'created_desc',
};

export const requestsListQuery = (filters: RequestsListQueryFilters = {}) => ({
  queryKey: requestKeys.list(filters),
  queryFn: ({ pageParam, signal }: { pageParam: number; signal: AbortSignal }) =>
    requestsApi.list({ ...filters, page: pageParam, perPage: REQUESTS_PAGE_SIZE }, signal),
  initialPageParam: 1,
  getNextPageParam: (lastPage: RequestsResponse) =>
    lastPage.page * lastPage.per_page < lastPage.total ? lastPage.page + 1 : undefined,
});

export const requestDetailQuery = (id: string) => ({
  queryKey: requestKeys.detail(id),
  queryFn: ({ signal }: { signal: AbortSignal }) => requestsApi.detail(id, signal),
});

export function useRequestsList(filters: RequestsListQueryFilters = {}) {
  const query = useInfiniteQuery(requestsListQuery(filters));

  return {
    ...query,
    requests: query.data?.pages.flatMap((page) => page.requests) ?? [],
    total: query.data?.pages[0]?.total ?? 0,
  };
}

export function useRequest(id: string | undefined) {
  return useQuery({
    ...requestDetailQuery(id ?? ''),
    enabled: Boolean(id),
  });
}

/**
 * The episodes of the season a request covers. Only a series has them, and a
 * request Sonarr has not linked to a series yet has none to report, which the
 * backend answers with a conflict rather than an empty list - so the caller
 * decides whether to ask at all.
 */
export function useRequestEpisodes(id: string | undefined, enabled = true) {
  return useQuery({
    queryKey: requestKeys.episodes(id ?? ''),
    queryFn: ({ signal }) => requestsApi.episodes(id ?? '', signal),
    enabled: Boolean(id) && enabled,
  });
}

/**
 * The seasons of the series a request belongs to. Kept out of the detail query
 * because it costs a call to Sonarr, and only the season manager needs it.
 */
export function useRequestSeasons(id: string | undefined, enabled = true) {
  return useQuery({
    queryKey: requestKeys.seasons(id ?? ''),
    queryFn: ({ signal }) => requestsApi.seasons(id ?? '', signal),
    enabled: Boolean(id) && enabled,
  });
}

export function useUpdateRequestSeasons(id: string | undefined) {
  const queryClient = useQueryClient();
  const { t } = useTranslation();

  return useMutation({
    mutationFn: (payload: UpdateSeasonsPayload) => requestsApi.updateSeasons(id ?? '', payload),
    onSuccess: (seasons) => {
      queryClient.setQueryData(requestKeys.seasons(id ?? ''), seasons);
      notifications.show({
        message: t('requestPage.seasons.saved'),
        color: 'teal',
      });
      // Seasons may have been added or withdrawn, so the request list and the
      // search results that report their state are both out of date.
      void queryClient.invalidateQueries({ queryKey: requestKeys.lists() });
      void queryClient.invalidateQueries({ queryKey: discoverKeys.all });
    },
    onError: (error: unknown) => {
      notifications.show({
        title: t('requestPage.seasons.saveFailed'),
        message: getErrorMessage(error, ''),
        color: 'red',
      });
    },
  });
}

export function useRemoveRequest() {
  const queryClient = useQueryClient();
  const { t } = useTranslation();

  return useMutation({
    mutationFn: (id: string) => requestsApi.remove(id),
    onSuccess: (_data, id) => {
      queryClient.removeQueries({ queryKey: requestKeys.detail(id) });
      notifications.show({
        message: t('requestPage.remove.removed'),
        color: 'teal',
      });
      void queryClient.invalidateQueries({ queryKey: requestKeys.lists() });
      void queryClient.invalidateQueries({ queryKey: discoverKeys.all });
    },
    onError: (error: unknown) => {
      notifications.show({
        title: t('requestPage.remove.failed'),
        message: getErrorMessage(error, ''),
        color: 'red',
      });
    },
  });
}

export function useUpdateRequestOwner(id: string | undefined) {
  const queryClient = useQueryClient();
  const { t } = useTranslation();

  return useMutation({
    mutationFn: (ownerUserId: string | null) => requestsApi.updateOwner(id ?? '', ownerUserId),
    onSuccess: (updated) => {
      queryClient.setQueryData(requestKeys.detail(id ?? ''), updated);
      notifications.show({ message: t('requestPage.owner.saved'), color: 'teal' });
      void queryClient.invalidateQueries({ queryKey: requestKeys.lists() });
    },
    onError: (error: unknown) => {
      notifications.show({
        title: t('requestPage.owner.saveFailed'),
        message: getErrorMessage(error, ''),
        color: 'red',
      });
    },
  });
}
