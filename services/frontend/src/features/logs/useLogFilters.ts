import { useSearchParams } from 'react-router-dom';

import { DEFAULT_LOG_SERVICE, isLogService } from '@/features/logs/services';
import { isTaskKind } from '@/features/tasks/formatting';
import type { LogService, SyncJobKind } from '@/types';

/** Keeps the log page's process and task filters in the URL so views are shareable. */
export function useLogFilters() {
  const [searchParams, setSearchParams] = useSearchParams();

  const serviceParam = searchParams.get('service');
  const taskParam = searchParams.get('task');

  const service: LogService = isLogService(serviceParam) ? serviceParam : DEFAULT_LOG_SERVICE;
  const task: SyncJobKind | undefined = isTaskKind(taskParam) ? taskParam : undefined;

  /*
   * Every change a single interaction makes has to travel in one call. React
   * Router builds the next URL from the params this render saw, so a second call
   * in the same tick starts from the same place and undoes the first.
   */
  const update = (changes: Record<string, string | null>) => {
    const next = new URLSearchParams(searchParams);
    for (const [key, value] of Object.entries(changes)) {
      if (value) {
        next.set(key, value);
      } else {
        next.delete(key);
      }
    }
    setSearchParams(next, { replace: true });
  };

  return {
    service,
    task,
    setService: (value: LogService) => {
      // Re-clicking the tab already showing must not disturb what is filtered.
      if (value === service) return;
      // A task is only ever logged by the process that ran it, so a task filter
      // carried across to the other one could only ever match nothing.
      update({ service: value === DEFAULT_LOG_SERVICE ? null : value, task: null });
    },
    setTask: (value: SyncJobKind | undefined) => update({ task: value ?? null }),
  };
}
