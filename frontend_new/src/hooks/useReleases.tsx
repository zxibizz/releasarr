import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationOptions,
  type UseQueryOptions,
} from '@tanstack/react-query';

import { releasesApi } from '@/features/releases/api';
import {
  releasesKeys,
  type ReleaseDetailQueryKey,
  type ReleaseListFilters,
  type ReleasesByRequestQueryKey,
  type ReleasesListQueryKey,
} from '@/features/releases/queryKeys';
import type { Release, ReleaseFileMappingInput } from '@/types';

const missingReleaseIdError = new Error('Release identifier is required');
const missingRequestIdError = new Error('Request identifier is required');

type ReleasesQueryOptions<TData> = Omit<
  UseQueryOptions<Release[], unknown, TData, ReleasesListQueryKey>,
  'queryKey' | 'queryFn'
>;

type ReleasesByRequestOptions<TData> = Omit<
  UseQueryOptions<Release[], unknown, TData, ReleasesByRequestQueryKey>,
  'queryKey' | 'queryFn'
>;

type ReleaseQueryOptions<TData> = Omit<
  UseQueryOptions<Release, unknown, TData, ReleaseDetailQueryKey>,
  'queryKey' | 'queryFn'
>;

type UpdateFileMappingsVariables = {
  releaseId: string;
  mappings: ReleaseFileMappingInput[];
};

type UpdateFileMappingsOptions = Omit<
  UseMutationOptions<boolean, unknown, UpdateFileMappingsVariables>,
  'mutationFn'
>;

export const useReleasesQuery = <TData = Release[],>(
  filters?: ReleaseListFilters,
  options?: ReleasesQueryOptions<TData>,
) => {
  return useQuery({
    queryKey: releasesKeys.list(filters),
    queryFn: () => releasesApi.list(filters),
    ...options,
  });
};

export const useReleasesByRequestQuery = <TData = Release[],>(
  requestId: string | undefined,
  options?: ReleasesByRequestOptions<TData>,
) => {
  const { enabled: optionEnabled, ...restOptions } = options ?? {};

  return useQuery({
    queryKey: requestId ? releasesKeys.byRequest(requestId) : ['releases', 'by-request', 'missing'],
    queryFn: () => {
      if (!requestId) {
        throw missingRequestIdError;
      }
      return releasesApi.byRequest(requestId);
    },
    enabled: Boolean(requestId) && (optionEnabled ?? true),
    ...restOptions,
  });
};

export const useReleasesByStatusQuery = <TData = Release[],>(
  status: Release['status'] | undefined,
  options?: ReleasesQueryOptions<TData>,
) => {
  const { enabled: optionEnabled, ...restOptions } = options ?? {};

  return useQuery({
    queryKey: releasesKeys.list(status ? { status } : undefined),
    queryFn: () => {
      if (!status) {
        throw new Error('Release status is required');
      }
      return releasesApi.byStatus(status);
    },
    enabled: Boolean(status) && (optionEnabled ?? true),
    ...restOptions,
  });
};

export const useReleaseQuery = <TData = Release,>(
  id: string | undefined,
  options?: ReleaseQueryOptions<TData>,
) => {
  const { enabled: optionEnabled, ...restOptions } = options ?? {};

  return useQuery({
    queryKey: id ? releasesKeys.detail(id) : ['releases', 'detail', 'missing'],
    queryFn: () => {
      if (!id) {
        throw missingReleaseIdError;
      }
      return releasesApi.detail(id);
    },
    enabled: Boolean(id) && (optionEnabled ?? true),
    ...restOptions,
  });
};

export const useReleaseFileMapping = (options?: UpdateFileMappingsOptions) => {
  const queryClient = useQueryClient();

  const mutation = useMutation<boolean, unknown, UpdateFileMappingsVariables>({
    mutationFn: ({ releaseId, mappings }) => releasesApi.updateFileMappings(releaseId, mappings),
    async onSuccess(_, { releaseId }) {
      await queryClient.invalidateQueries({
        queryKey: releasesKeys.detail(releaseId),
        exact: true,
      });
      await queryClient.invalidateQueries({ queryKey: releasesKeys.all });
      await queryClient.invalidateQueries({ queryKey: releasesKeys.list(undefined), exact: false });
      await queryClient.invalidateQueries({ queryKey: ['releases', 'by-request'], exact: false });
    },
    ...options,
  });

  const updateFileMappings = async (releaseId: string, mappings: ReleaseFileMappingInput[]) => {
    if (!releaseId) {
      throw missingReleaseIdError;
    }

    try {
      return await mutation.mutateAsync({ releaseId, mappings });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to update file mapping';
      throw new Error(message);
    }
  };

  return {
    updateFileMappings,
    loading: mutation.isPending,
    error:
      mutation.error instanceof Error
        ? mutation.error.message
        : mutation.error
          ? String(mutation.error)
          : null,
  };
};

export const useReleaseActions = () => {
  const mutation = useMutation({
    mutationFn: (action: () => Promise<unknown>) => action(),
  });

  const performAction = async (action: () => Promise<unknown>) => {
    try {
      return await mutation.mutateAsync(action);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Action failed';
      throw new Error(message);
    }
  };

  return {
    performAction,
    loading: mutation.isPending,
    error:
      mutation.error instanceof Error
        ? mutation.error.message
        : mutation.error
          ? String(mutation.error)
          : null,
  };
};
