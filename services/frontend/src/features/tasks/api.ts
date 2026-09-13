import { apiRequest } from '@/lib/api/client';
import type {
  AsyncOperationResponse,
  ScheduledTask,
  ScheduledTasksResponse,
  SyncJob,
  SyncJobKind,
  SyncJobsResponse,
} from '@/types';

const encode = encodeURIComponent;

export const tasksApi = {
  /** Queue every task. Runs in the scheduler process, not the API. */
  syncAll: () => apiRequest<AsyncOperationResponse>('/tasks/sync_all', { method: 'POST' }),

  /** Queue a single task, as the run button next to each task does. */
  run: (kind: SyncJobKind) =>
    apiRequest<AsyncOperationResponse>(`/tasks/run/${encode(kind)}`, { method: 'POST' }),

  scheduled: async (signal?: AbortSignal): Promise<ScheduledTask[]> => {
    const response = await apiRequest<ScheduledTasksResponse>('/tasks/scheduled', { signal });
    return response.tasks;
  },

  recentJobs: async (limit = 20, signal?: AbortSignal): Promise<SyncJob[]> => {
    const response = await apiRequest<SyncJobsResponse>('/tasks/jobs', {
      signal,
      query: { limit },
    });
    return response.jobs;
  },

  job: (jobId: string, signal?: AbortSignal) =>
    apiRequest<SyncJob>(`/tasks/jobs/${encode(jobId)}`, { signal }),
};
