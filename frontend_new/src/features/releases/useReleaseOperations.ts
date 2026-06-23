import { useToast } from '@chakra-ui/react';
import { useMutation, useQueryClient, type QueryKey } from '@tanstack/react-query';
import { useCallback } from 'react';

import { releasesApi } from '@/features/releases/api';
import { releasesKeys } from '@/features/releases/queryKeys';
import type { Release } from '@/types';

interface OperationOptions {
  onSuccess?: () => void;
}

interface DeleteMutationContext {
  previousLists: Array<[QueryKey, Release[] | undefined]>;
  previousDetail?: Release;
}

export const useReleaseOperations = (requestId?: string) => {
  const queryClient = useQueryClient();
  const toast = useToast();

  const invalidateReleaseQueries = useCallback(async () => {
    const tasks: Array<Promise<unknown>> = [
      queryClient.invalidateQueries({ queryKey: releasesKeys.all }),
      queryClient.invalidateQueries({ queryKey: releasesKeys.list(undefined), exact: false }),
    ];

    if (requestId) {
      tasks.push(
        queryClient.invalidateQueries({ queryKey: releasesKeys.byRequest(requestId), exact: true }),
      );
      tasks.push(
        queryClient.invalidateQueries({ queryKey: releasesKeys.list({ requestId }), exact: true }),
      );
    }

    await Promise.all(tasks);
  }, [queryClient, requestId]);

  const handleError = useCallback(
    (title: string, error: unknown) => {
      const message = error instanceof Error ? error.message : undefined;
      toast({
        title,
        description: message,
        status: 'error',
        duration: 4000,
        isClosable: true,
      });
    },
    [toast],
  );

  const deleteMutation = useMutation<void, unknown, string, DeleteMutationContext>({
    mutationFn: (releaseId: string) => releasesApi.delete(releaseId),
    retry: 1,
    async onMutate(releaseId) {
      await queryClient.cancelQueries({ queryKey: ['releases'] });

      const previousLists = queryClient.getQueriesData<Release[]>({
        queryKey: ['releases', 'list'],
      });

      const previousDetail = queryClient.getQueryData<Release>(releasesKeys.detail(releaseId));

      previousLists.forEach(([queryKey, data]) => {
        if (!data) {
          return;
        }
        queryClient.setQueryData<Release[]>(queryKey, data.filter((release) => release.id !== releaseId));
      });

      queryClient.removeQueries({ queryKey: releasesKeys.detail(releaseId), exact: true });

      return { previousLists, previousDetail };
    },
    onError(error, releaseId, context) {
      context?.previousLists.forEach(([queryKey, data]) => {
        queryClient.setQueryData(queryKey, data);
      });

      if (context?.previousDetail) {
        queryClient.setQueryData(releasesKeys.detail(releaseId), context.previousDetail);
      }

      handleError('Failed to delete release', error);
    },
    onSuccess() {
      toast({
        title: 'Release deleted',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
    },
    async onSettled() {
      await invalidateReleaseQueries();
    },
  });

  const pauseMutation = useMutation({
    mutationFn: (releaseId: string) => releasesApi.pause(releaseId),
    retry: 1,
    onError(error) {
      handleError('Failed to pause release', error);
    },
    onSuccess() {
      toast({
        title: 'Release paused',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
    },
    async onSettled() {
      await invalidateReleaseQueries();
    },
  });

  const resumeMutation = useMutation({
    mutationFn: (releaseId: string) => releasesApi.resume(releaseId),
    retry: 1,
    onError(error) {
      handleError('Failed to resume release', error);
    },
    onSuccess() {
      toast({
        title: 'Release resumed',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
    },
    async onSettled() {
      await invalidateReleaseQueries();
    },
  });

  const deleteRelease = useCallback(
    async (releaseId: string, options?: OperationOptions) => {
      await deleteMutation.mutateAsync(releaseId, {
        onSuccess: () => options?.onSuccess?.(),
      });
    },
    [deleteMutation],
  );

  const pauseRelease = useCallback(
    async (releaseId: string, options?: OperationOptions) => {
      await pauseMutation.mutateAsync(releaseId, {
        onSuccess: () => options?.onSuccess?.(),
      });
    },
    [pauseMutation],
  );

  const resumeRelease = useCallback(
    async (releaseId: string, options?: OperationOptions) => {
      await resumeMutation.mutateAsync(releaseId, {
        onSuccess: () => options?.onSuccess?.(),
      });
    },
    [resumeMutation],
  );

  return {
    deleteRelease,
    pauseRelease,
    resumeRelease,
  } as const;
};
