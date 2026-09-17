import type { LogComponent } from '@/types';

/**
 * Every component the backend can log under, grouped by the dotted prefix that
 * names its layer. The order is the order the filter groups appear in.
 *
 * The `LogComponent[]` annotation keeps the list honest: a value added to the
 * backend enum but forgotten here is a type error, not a silently missing
 * filter option.
 */
export const LOG_COMPONENTS: LogComponent[] = [
  'api.http',
  'api.error',
  'api.auth',
  'scheduler',
  'scheduler.jobs',
  'task.release_sync',
  'task.release_summary',
  'usecase.add_request',
  'usecase.auto_mapping',
  'usecase.auth',
  'usecase.create_release',
  'usecase.delete_release',
  'usecase.delete_request',
  'usecase.enqueue_job',
  'usecase.export',
  'usecase.file_mappings',
  'usecase.grab',
  'usecase.indexers',
  'usecase.queue_download',
  'usecase.queue_manual',
  'usecase.recompute_state',
  'usecase.refresh_releases',
  'usecase.regrab',
  'usecase.regrab_outdated',
  'usecase.release_search',
  'usecase.replace_existing',
  'usecase.search_media',
  'usecase.sync_radarr',
  'usecase.sync_sonarr',
  'usecase.update_seasons',
  'usecase.users',
  'integration.prowlarr',
  'integration.qbittorrent',
  'integration.radarr',
  'integration.sonarr',
  'integration.tmdb',
  'integration.tvdb',
];

/** The prefix groups, in the order the filter shows them. */
export const LOG_COMPONENT_GROUPS = ['api', 'scheduler', 'task', 'usecase', 'integration'] as const;

export type LogComponentGroup = (typeof LOG_COMPONENT_GROUPS)[number];

export const isLogComponent = (value: unknown): value is LogComponent =>
  LOG_COMPONENTS.includes(value as LogComponent);

/** Group the components for the filter's option groups, preserving order. */
export const componentsByGroup = (): Record<LogComponentGroup, LogComponent[]> => {
  const grouped = {} as Record<LogComponentGroup, LogComponent[]>;
  for (const group of LOG_COMPONENT_GROUPS) {
    grouped[group] = [];
  }
  for (const component of LOG_COMPONENTS) {
    const prefix = component.split('.')[0] as LogComponentGroup;
    grouped[prefix].push(component);
  }
  return grouped;
};
