import { notifications } from '@mantine/notifications';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';

import { releasesApi } from '@/features/releases/api';
import { taskKeys } from '@/features/tasks/queries';
import type { ReleaseFileMappingInput } from '@/types';
import { getErrorMessage } from '@/utils/errors';

export const releaseKeys = {
  all: ['releases'] as const,
  byRequest: (requestId: string) => [...releaseKeys.all, 'by-request', requestId] as const,
  mappingSuggestions: (releaseId: string) =>
    [...releaseKeys.all, 'mapping-suggestions', releaseId] as const,
};

export const releasesByRequestQuery = (requestId: string) => ({
  queryKey: releaseKeys.byRequest(requestId),
  queryFn: ({ signal }: { signal: AbortSignal }) => releasesApi.byRequest(requestId, signal),
});

export function useReleasesByRequest(requestId: string | undefined) {
  return useQuery({
    ...releasesByRequestQuery(requestId ?? ''),
    enabled: Boolean(requestId),
  });
}

/**
 * Pause/resume/delete actions for a release, scoped to the request page that
 * owns them so the correct list is refreshed afterwards.
 */
export function useReleaseActions(requestId: string | undefined) {
  const queryClient = useQueryClient();
  const { t } = useTranslation();

  const invalidate = () =>
    queryClient.invalidateQueries({
      queryKey: requestId ? releaseKeys.byRequest(requestId) : releaseKeys.all,
    });

  const run = (
    action: (releaseId: string) => Promise<unknown>,
    successMessage: string,
    errorMessage: string,
  ) => ({
    mutationFn: action,
    onSuccess: () => {
      notifications.show({ message: successMessage, color: 'teal' });
    },
    onError: (error: unknown) => {
      notifications.show({
        title: errorMessage,
        message: getErrorMessage(error, ''),
        color: 'red',
      });
    },
    onSettled: invalidate,
  });

  const pause = useMutation(
    run(
      releasesApi.pause,
      t('releaseActions.paused', { defaultValue: 'Release paused' }),
      t('releaseActions.pauseFailed', { defaultValue: 'Failed to pause release' }),
    ),
  );

  const resume = useMutation(
    run(
      releasesApi.resume,
      t('releaseActions.resumed', { defaultValue: 'Release resumed' }),
      t('releaseActions.resumeFailed', { defaultValue: 'Failed to resume release' }),
    ),
  );

  const remove = useMutation(
    run(
      releasesApi.remove,
      t('releaseActions.deleted', { defaultValue: 'Release deleted' }),
      t('releaseActions.deleteFailed', { defaultValue: 'Failed to delete release' }),
    ),
  );

  return { pause, resume, remove };
}

export function useUpdateFileMappings(releaseId: string, requestId: string | undefined) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (files: ReleaseFileMappingInput[]) =>
      releasesApi.updateFileMappings(releaseId, files),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: requestId ? releaseKeys.byRequest(requestId) : releaseKeys.all,
      });
      // Saving part of a release leaves the rest to propose again.
      void queryClient.invalidateQueries({
        queryKey: releaseKeys.mappingSuggestions(releaseId),
      });
      // A release that already finished downloading is exported again on the
      // spot, so pick that job up and let the watcher report how it went.
      void queryClient.invalidateQueries({ queryKey: taskKeys.jobsRoot });
    },
  });
}

/**
 * The mappings the server would apply to a release's files, which it works out
 * from the file names and the requests currently on the table. Nothing is
 * stored until the form saves, so this is only ever a starting point.
 */
export function useSuggestedFileMappings(releaseId: string | undefined) {
  return useQuery({
    queryKey: releaseKeys.mappingSuggestions(releaseId ?? ''),
    queryFn: ({ signal }: { signal: AbortSignal }) =>
      releasesApi.suggestedFileMappings(releaseId ?? '', signal),
    enabled: Boolean(releaseId),
    // The requests a file may map to change as the library does, so a cached
    // answer from an earlier visit is not one worth reusing.
    staleTime: 0,
  });
}
