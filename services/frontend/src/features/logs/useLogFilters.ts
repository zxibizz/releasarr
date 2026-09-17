import { useSearchParams } from 'react-router-dom';

import { isLogComponent } from '@/features/logs/components';
import { isLogService } from '@/features/logs/services';
import type { LogComponent, LogService } from '@/types';

/**
 * Keeps the log page's filters in the URL so a narrowed view is shareable.
 *
 * There is one merged stream now, so no tab owns a process: `service` and
 * `component` are both optional and both reset to "all" when absent.
 */
export function useLogFilters() {
  const [searchParams, setSearchParams] = useSearchParams();

  const serviceParam = searchParams.get('service');
  const componentParam = searchParams.get('component');

  const service: LogService | undefined = isLogService(serviceParam) ? serviceParam : undefined;
  const component: LogComponent | undefined = isLogComponent(componentParam)
    ? componentParam
    : undefined;

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
    component,
    setService: (value: LogService | undefined) => update({ service: value ?? null }),
    setComponent: (value: LogComponent | undefined) => update({ component: value ?? null }),
  };
}
