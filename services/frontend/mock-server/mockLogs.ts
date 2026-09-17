import type { MediaRequest, RequestLogEntry, SyncJobKind } from '../src/types';

const formatTimestamp = (date: Date) =>
  date.toLocaleString(undefined, {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    year: 'numeric',
    month: 'short',
    day: '2-digit',
  });

const minutesAgo = (baseDate: Date, minutes: number) =>
  new Date(baseDate.getTime() - minutes * 60 * 1000);

const buildLog = (
  baseDate: Date,
  minutes: number,
  entry: Omit<RequestLogEntry, 'occurredAt' | 'timestamp'>,
): RequestLogEntry => {
  const occurredAtDate = minutesAgo(baseDate, minutes);
  return {
    ...entry,
    occurredAt: occurredAtDate.getTime(),
    timestamp: formatTimestamp(occurredAtDate),
  };
};

/**
 * A line the mock "writes" while serving a request, stamped at the moment it
 * happened the way the backend's log file would.
 */
export const stampLogEntry = (
  entry: Omit<RequestLogEntry, 'occurredAt' | 'timestamp'>,
): RequestLogEntry => buildLog(new Date(), 0, entry);

export const generateMockRequestLogs = (request: MediaRequest): RequestLogEntry[] => {
  const now = new Date();

  // Every entry binds the snake_case `request_id` the backend's log reader matches
  // `?request_id=` on, so the per-request view actually finds these.
  const logs: RequestLogEntry[] = [
    buildLog(now, 240, {
      id: `${request.id}-log-1`,
      level: 'info',
      message: `Request received for ${request.title}.`,
      source: 'src.api.routes.discover',
      component: 'api.http',
      metadata: {
        request_id: request.id,
        statusCode: 201,
        mediaType: request.type,
      },
    }),
    buildLog(now, 195, {
      id: `${request.id}-log-2`,
      level: 'info',
      message: 'Added series requests',
      source: 'src.application.use_cases.discover.add_request',
      component: 'usecase.add_request',
      metadata: {
        request_id: request.id,
        title: request.title,
        requests: 1,
      },
    }),
    buildLog(now, 160, {
      id: `${request.id}-log-3`,
      level: 'info',
      message: 'Synced request from Sonarr',
      source: 'src.application.use_cases.requests.sync_sonarr',
      component: 'usecase.sync_sonarr',
      metadata: {
        request_id: request.id,
        status: 'searching',
      },
    }),
    buildLog(now, 90, {
      id: `${request.id}-log-4`,
      level: 'info',
      message: 'Release search started',
      source: 'src.application.use_cases.releases.search_release_sources',
      component: 'usecase.release_search',
      metadata: {
        request_id: request.id,
        query: `${request.title} S01`,
        indexers: 5,
      },
    }),
    buildLog(now, 72, {
      id: `${request.id}-log-5`,
      level: 'warning',
      message: 'Indexer response delayed beyond SLA.',
      source: 'src.infrastructure.prowlarr.service',
      component: 'integration.prowlarr',
      metadata: {
        request_id: request.id,
        timeoutMs: 30000,
      },
    }),
    buildLog(now, 58, {
      id: `${request.id}-log-6`,
      level: 'error',
      message: 'Grab failed: the download client rejected the torrent.',
      source: 'src.application.use_cases.releases.queue_release_download',
      component: 'usecase.queue_download',
      metadata: {
        request_id: request.id,
        release_id: 'rls-15873',
        error: 'qBittorrent returned 403',
      },
      stackTrace: [
        'Traceback (most recent call last):',
        '  File "src/application/use_cases/releases/queue_release_download.py", line 112, in execute',
        '    await self._download_service.queue_download(...)',
        'httpx.HTTPStatusError: 403 Forbidden',
      ].join('\n'),
    }),
    buildLog(now, 25, {
      id: `${request.id}-log-7`,
      level: 'info',
      message: 'Grabbed release Some.Show.S01E05.1080p',
      source: 'src.application.use_cases.releases.queue_release_download',
      component: 'usecase.queue_download',
      metadata: {
        request_id: request.id,
        release_id: 'rls-15873',
        release_name: 'Some.Show.S01E05.1080p',
        source: 'Indexer A',
        quality: '1080p',
      },
    }),
    // The hourly re-grab check has its own line per release it looked at, so the
    // fixture carries one rather than leaving the shape to the live appends.
    buildLog(now, 33, {
      id: `${request.id}-log-8`,
      level: 'info',
      message: 'Release is up to date on its indexer',
      source: 'src.application.use_cases.releases.regrab',
      component: 'usecase.regrab',
      metadata: {
        request_id: request.id,
        release_id: 'rls-15873',
        release_name: 'Some.Show.S01E05.1080p.WEB-DL',
        indexer: 'Indexer A',
        info_hash: 'a1b2c3d4',
      },
    }),
  ];

  logs.sort((a, b) => b.occurredAt - a.occurredAt);
  // Mirrors the API process, which stamps every record it writes.
  return logs.map((log) => ({ ...log, metadata: { ...log.metadata, service: 'api' } }));
};

type TaskLogSeed = {
  task: SyncJobKind;
  level: RequestLogEntry['level'];
  message: string;
  source: string;
  component: RequestLogEntry['component'];
  metadata?: Record<string, unknown>;
  stackTrace?: string;
};

/** Mirrors the backend, which tags every line logged while a task runs. */
const TASK_LOG_SEEDS: TaskLogSeed[] = [
  {
    task: 'sonarr_sync',
    level: 'info',
    message: 'Sonarr sync finished',
    source: 'src.application.use_cases.requests.sync_sonarr',
    component: 'usecase.sync_sonarr',
    metadata: { created: 0, updated: 2, completed: 1 },
  },
  {
    task: 'sonarr_sync',
    level: 'error',
    message: "request to '/wanted/missing' failed: All connection attempts failed",
    source: 'src.tasks.scheduler_service',
    component: 'scheduler',
    stackTrace: [
      'Traceback (most recent call last):',
      '  File "src/tasks/scheduler_service.py", line 130, in _run_scheduled',
      '    summary = await self.steps.for_kind(kind)()',
      'httpx.ConnectError: All connection attempts failed',
    ].join('\n'),
  },
  {
    task: 'radarr_sync',
    level: 'info',
    message: 'Radarr sync finished',
    source: 'src.application.use_cases.requests.sync_radarr',
    component: 'usecase.sync_radarr',
    metadata: { created: 1, updated: 1, completed: 0 },
  },
  {
    task: 'release_sync',
    level: 'info',
    message: 'Request status changed from downloading to completed',
    source: 'src.tasks.sync_releases',
    component: 'task.release_sync',
    metadata: { previous_status: 'downloading', status: 'completed' },
  },
  {
    task: 'release_sync',
    level: 'warning',
    message: 'Torrent no longer present in the download client',
    source: 'src.tasks.sync_releases',
    component: 'task.release_sync',
    metadata: { release_id: 'rls-15873' },
  },
  {
    task: 'export',
    level: 'info',
    message: 'Imported a release into Sonarr',
    source: 'src.application.use_cases.releases.export_finished',
    component: 'usecase.export',
    metadata: { release_name: 'Some.Show.S02E04.1080p' },
  },
  {
    task: 'export',
    level: 'info',
    message: 'Imported a release into Radarr',
    source: 'src.application.use_cases.releases.export_finished',
    component: 'usecase.export',
    metadata: { release_name: 'Some.Movie.2019.1080p.BluRay.x264' },
  },
  {
    task: 'export',
    level: 'info',
    message: 'Task complete',
    source: 'src.tasks.sync_jobs',
    component: 'scheduler.jobs',
    metadata: { job_id: 'a1b2c3d4', trigger: 'download_client' },
  },
  {
    task: 'regrab',
    level: 'info',
    message: 'No outdated releases found',
    source: 'src.application.use_cases.releases.regrab_outdated',
    component: 'usecase.regrab_outdated',
  },
];

/** Repeats the seeds over the last few hours so pagination has something to page. */
export const generateMockTaskLogs = (): RequestLogEntry[] => {
  const now = new Date();

  const logs = Array.from({ length: 6 }).flatMap((_, round) =>
    TASK_LOG_SEEDS.map((seed, index) => {
      const minutes = round * 30 + index * 2;
      const { task, metadata, component, ...rest } = seed;

      return buildLog(now, minutes, {
        ...rest,
        id: `task-log-${round}-${index}`,
        component,
        // Mirrors the scheduler process, which stamps every record it writes.
        metadata: { ...metadata, task, service: 'scheduler' },
      });
    }),
  );

  logs.sort((a, b) => b.occurredAt - a.occurredAt);
  return logs;
};
