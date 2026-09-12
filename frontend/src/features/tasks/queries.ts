import { notifications } from '@mantine/notifications';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';

import { releaseKeys } from '@/features/releases/queries';
import { requestKeys } from '@/features/requests/queries';
import { tasksApi } from '@/features/tasks/api';
import type { SyncJob, SyncJobKind, SyncJobStatus } from '@/types';
import { getErrorMessage } from '@/utils/errors';

const jobsRoot = ['tasks', 'jobs'] as const;

export const taskKeys = {
  all: ['tasks'] as const,
  /** Prefix matching every job list, whatever its page size. */
  jobsRoot,
  jobs: (limit: number) => [...jobsRoot, { limit }] as const,
  scheduled: () => ['tasks', 'scheduled'] as const,
};

const ACTIVE_STATUSES = new Set<SyncJobStatus>(['queued', 'running']);
const POLL_INTERVAL_MS = 2_000;
/** Keeps "next execution" honest without hammering the API. */
const SCHEDULED_POLL_INTERVAL_MS = 10_000;
/** A job still waiting this long means nothing is draining the queue. */
const STALLED_AFTER_MS = 2 * 60_000;
/**
 * How many runs the queue table shows. The app-wide watcher requests the same
 * number so both share one cache entry, and therefore one poll.
 */
export const JOB_HISTORY_LIMIT = 20;

export const isActiveJob = (job: SyncJob) => ACTIVE_STATUSES.has(job.status);

export const isStalledJob = (job: SyncJob) =>
  Date.now() - new Date(job.queued_at).getTime() > STALLED_AFTER_MS;

/**
 * Recent job history, polled while anything is still queued or running.
 *
 * Polling also stops once the oldest active job looks stalled, so a scheduler
 * that is down cannot leave the UI spinning forever.
 */
export function useSyncJobs(limit: number) {
  return useQuery({
    queryKey: taskKeys.jobs(limit),
    queryFn: ({ signal }) => tasksApi.recentJobs(limit, signal),
    refetchInterval: ({ state }) => {
      const active = state.data?.filter(isActiveJob) ?? [];
      if (active.length === 0) return false;
      return active.some((job) => !isStalledJob(job)) ? POLL_INTERVAL_MS : false;
    },
  });
}

/**
 * Announces finished syncs and refreshes the data they changed.
 *
 * Mounted once, app-wide. Anything else that renders job data should use
 * {@link useSyncJobs}, or the notifications would fire more than once per job.
 */
export function useSyncWatcher(): void {
  const query = useSyncJobs(JOB_HISTORY_LIMIT);

  useSyncCompletionEffects(query.data?.[0]);
}

export function useScheduledTasks() {
  return useQuery({
    queryKey: taskKeys.scheduled(),
    queryFn: ({ signal }) => tasksApi.scheduled(signal),
    refetchInterval: SCHEDULED_POLL_INTERVAL_MS,
  });
}

/**
 * Refreshes request and release data once a sync finishes, since that is when
 * imported episodes and new download state become visible.
 */
function useSyncCompletionEffects(latest: SyncJob | undefined) {
  const queryClient = useQueryClient();
  const { t } = useTranslation();
  const seen = useRef<{ id: string; status: SyncJobStatus } | null>(null);

  useEffect(() => {
    if (!latest) return;

    const previous = seen.current;
    seen.current = { id: latest.id, status: latest.status };

    const justFinished =
      previous?.id === latest.id &&
      ACTIVE_STATUSES.has(previous.status) &&
      !ACTIVE_STATUSES.has(latest.status);

    if (!justFinished) return;

    void queryClient.invalidateQueries({ queryKey: requestKeys.all });
    void queryClient.invalidateQueries({ queryKey: releaseKeys.all });

    if (latest.status === 'completed') {
      notifications.show({
        message: t('tasks.toasts.finished', { defaultValue: 'Sync finished' }),
        color: 'teal',
      });
      return;
    }

    notifications.show({
      title: t('tasks.toasts.failedTitle', { defaultValue: 'Sync failed' }),
      message: latest.error ?? t('tasks.toasts.failedFallback', { defaultValue: '' }),
      color: 'red',
    });
  }, [latest, queryClient, t]);
}

function useQueueNotifications() {
  const { t } = useTranslation();

  return {
    onSuccess: (message: string | null | undefined) => {
      notifications.show({
        message: message ?? t('tasks.toasts.queued', { defaultValue: 'Sync queued' }),
        color: 'blue',
      });
    },
    onError: (error: unknown) => {
      notifications.show({
        title: t('tasks.toasts.queueFailedTitle', { defaultValue: 'Could not queue sync' }),
        message: getErrorMessage(
          error,
          t('tasks.toasts.queueFailedFallback', { defaultValue: '' }),
        ),
        color: 'red',
      });
    },
  };
}

export function useTriggerFullSync() {
  const queryClient = useQueryClient();
  const notify = useQueueNotifications();

  return useMutation({
    mutationFn: tasksApi.syncAll,
    onSuccess: (response) => notify.onSuccess(response.message),
    onError: notify.onError,
    // Start tracking the jobs the scheduler is about to pick up.
    onSettled: () => queryClient.invalidateQueries({ queryKey: taskKeys.jobsRoot }),
  });
}

export function useRunTask() {
  const queryClient = useQueryClient();
  const notify = useQueueNotifications();

  return useMutation({
    mutationFn: (kind: SyncJobKind) => tasksApi.run(kind),
    onSuccess: (response) => notify.onSuccess(response.message),
    onError: notify.onError,
    onSettled: () => queryClient.invalidateQueries({ queryKey: taskKeys.jobsRoot }),
  });
}
