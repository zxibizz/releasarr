import {
  useQuery,
  useQueryClient,
  type QueryClient,
  type UseQueryOptions,
} from '@tanstack/react-query';
import { useMemo } from 'react';

import { requestsApi } from '@/features/requests/api';
import {
  requestsKeys,
  type RequestDetailQueryKey,
  type RequestListFilters,
  type RequestsListQueryKey,
} from '@/features/requests/queryKeys';
import type { MediaRequest, RequestsResponse } from '@/types';

const missingIdError = new Error('Request identifier is required');

type RequestsQueryOptions<TData> = Omit<
  UseQueryOptions<RequestsResponse, unknown, TData, RequestsListQueryKey>,
  'queryKey' | 'queryFn'
>;

type RequestQueryOptions<TData> = Omit<
  UseQueryOptions<MediaRequest, unknown, TData, RequestDetailQueryKey>,
  'queryKey' | 'queryFn'
>;

export const useRequestsQuery = <TData = RequestsResponse,>(
  filters?: RequestListFilters,
  options?: RequestsQueryOptions<TData>,
) => {
  return useQuery({
    queryKey: requestsKeys.list(filters),
    queryFn: () => requestsApi.list(filters),
    ...options,
  });
};

export const useRequestsList = (
  filters?: RequestListFilters,
  options?: RequestsQueryOptions<RequestsResponse>,
) => {
  const query = useRequestsQuery(filters, options);
  const list = useMemo(() => query.data?.requests ?? [], [query.data?.requests]);

  return {
    ...query,
    requests: list,
    total: query.data?.total ?? 0,
    page: query.data?.page ?? 1,
    perPage: query.data?.per_page ?? list.length,
  };
};

export const useRequestQuery = <TData = MediaRequest,>(
  id: string | undefined,
  options?: RequestQueryOptions<TData>,
) => {
  const { enabled: optionEnabled, ...restOptions } = options ?? {};

  return useQuery({
    queryKey: id ? requestsKeys.detail(id) : ['requests', 'detail', 'missing'],
    queryFn: () => {
      if (!id) {
        throw missingIdError;
      }
      return requestsApi.detail(id);
    },
    enabled: Boolean(id) && (optionEnabled ?? true),
    ...restOptions,
  });
};

export const usePrefetchRequest = () => {
  const queryClient = useQueryClient();

  return async (id: string) => {
    if (!id) {
      throw missingIdError;
    }

    await queryClient.prefetchQuery({
      queryKey: requestsKeys.detail(id),
      queryFn: () => requestsApi.detail(id),
    });
  };
};

export const useRefreshRequest = () => {
  const queryClient = useQueryClient();

  return async (id?: string) => {
    if (id) {
      await queryClient.invalidateQueries({ queryKey: requestsKeys.detail(id), exact: true });
    }
    await queryClient.invalidateQueries({ queryKey: requestsKeys.all });
  };
};

export const setRequestQueryData = (client: QueryClient, request: MediaRequest) => {
  client.setQueryData(requestsKeys.detail(request.id), request);
  client.invalidateQueries({ queryKey: requestsKeys.all, exact: false });
};
