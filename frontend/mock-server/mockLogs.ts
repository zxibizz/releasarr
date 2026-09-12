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

export const generateMockRequestLogs = (request: MediaRequest): RequestLogEntry[] => {
  const now = new Date();

  const logs: RequestLogEntry[] = [
    buildLog(now, 240, {
      id: `${request.id}-log-1`,
      level: 'info',
      message: `Request received for ${request.title}.`,
      source: 'Releasarr API',
      metadata: {
        requestId: request.id,
        user: 'alex',
        requestType: request.type,
      },
    }),
    buildLog(now, 195, {
      id: `${request.id}-log-2`,
      level: 'info',
      message: 'Request normalized and queued for metadata lookup.',
      source: 'Metadata Worker',
      metadata: {
        imdbId: request.imdb_id,
        retries: 0,
      },
    }),
    buildLog(now, 160, {
      id: `${request.id}-log-3`,
      level: 'warning',
      message:
        'Primary metadata provider returned partial response (missing release date, falling back to secondary provider).',
      source: 'Metadata Worker',
      metadata: {
        provider: 'TMDB',
        statusCode: 206,
      },
    }),
    buildLog(now, 140, {
      id: `${request.id}-log-4`,
      level: 'info',
      message: 'Secondary metadata provider completed merge.',
      source: 'Metadata Worker',
      metadata: {
        provider: 'OMDb',
        mergedFields: 4,
      },
    }),
    buildLog(now, 90, {
      id: `${request.id}-log-5`,
      level: 'info',
      message: 'Automatic release scan started across enabled indexers.',
      source: 'Scan Scheduler',
      metadata: {
        indexers: 5,
        categories: 'Movies-HD, Movies-4K',
      },
    }),
    buildLog(now, 72, {
      id: `${request.id}-log-6`,
      level: 'warning',
      message:
        'Indexer response delayed beyond SLA (timeout after 30s while querying 4 providers).',
      source: 'Indexer: Prowlarr',
      metadata: {
        timeoutMs: 30000,
        providers: 4,
      },
    }),
    buildLog(now, 58, {
      id: `${request.id}-log-7`,
      level: 'error',
      message: 'NZB provider responded with rate limit. Will retry in 15 minutes.',
      source: 'Indexer: NZBGeek',
      metadata: {
        retryInMinutes: 15,
        statusCode: 429,
      },
      stackTrace: [
        'Error: Rate limit exceeded',
        '    at RateLimitedFetcher.fetch (services/indexers/nzbgeek.ts:87:15)',
        '    at async runWithRetries (services/retry.ts:42:13)',
        '    at async scheduleIndexerScan (jobs/indexerScan.ts:66:5)',
      ].join('\n'),
    }),
    buildLog(now, 47, {
      id: `${request.id}-log-8`,
      level: 'info',
      message: 'Retry scheduled for rate-limited provider.',
      source: 'Job Runner',
      metadata: {
        jobId: `retry-${request.id}-nzbgeek`,
        attempt: 2,
      },
    }),
    buildLog(now, 25, {
      id: `${request.id}-log-9`,
      level: 'info',
      message: 'Manual search dispatched to secondary indexers.',
      source: 'Job Runner',
      metadata: {
        triggeredBy: 'alex',
        indexers: ['TorrentLeech', 'RARBG Mirror'].join(', '),
      },
    }),
    buildLog(now, 15, {
      id: `${request.id}-log-10`,
      level: 'info',
      message: 'Candidate release processed, awaiting quality approval.',
      source: 'Quality Gate',
      metadata: {
        releaseId: 'rls-15873',
        quality: '2160p UHD',
        score: 78,
      },
    }),
    buildLog(now, 6, {
      id: `${request.id}-log-11`,
      level: 'warning',
      message:
        'Quality gate rejected candidate due to codec mismatch (expected HEVC but found AVC).',
      source: 'Quality Gate',
      metadata: {
        releaseId: 'rls-15873',
        expectedCodec: 'HEVC',
        actualCodec: 'AVC',
      },
    }),
    buildLog(now, 2, {
      id: `${request.id}-log-12`,
      level: 'info',
      message: 'Awaiting next manual search input.',
      source: 'Job Runner',
      metadata: {
        pendingActions: 2,
      },
    }),
  ];

  logs.sort((a, b) => b.occurredAt - a.occurredAt);
  return logs;
};

type TaskLogSeed = {
  task: SyncJobKind;
  level: RequestLogEntry['level'];
  message: string;
  source: string;
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
    metadata: { component: 'sync_sonarr_requests', created: 0, updated: 2, completed: 1 },
  },
  {
    task: 'sonarr_sync',
    level: 'error',
    message: "request to '/wanted/missing' failed: All connection attempts failed",
    source: 'src.tasks.scheduler_service',
    metadata: { service: 'Scheduler' },
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
    metadata: { component: 'sync_radarr_requests', created: 1, updated: 1, completed: 0 },
  },
  {
    task: 'release_sync',
    level: 'info',
    message: 'Request status changed from downloading to completed',
    source: 'src.tasks.sync_releases',
    metadata: { previous_status: 'downloading', status: 'completed' },
  },
  {
    task: 'release_sync',
    level: 'warning',
    message: 'Torrent no longer present in the download client',
    source: 'src.tasks.sync_releases',
    metadata: { release_id: 'rls-15873' },
  },
  {
    task: 'export',
    level: 'info',
    message: 'Imported a release into Sonarr',
    source: 'src.application.use_cases.releases.export_finished',
    metadata: { component: 'export_finished_releases', release_name: 'Some.Show.S02E04.1080p' },
  },
  {
    task: 'export',
    level: 'info',
    message: 'Imported a release into Radarr',
    source: 'src.application.use_cases.releases.export_finished',
    metadata: {
      component: 'export_finished_releases',
      release_name: 'Some.Movie.2019.1080p.BluRay.x264',
    },
  },
  {
    task: 'export',
    level: 'info',
    message: 'Task complete',
    source: 'src.tasks.sync_jobs',
    metadata: { component: 'sync_job_runner', job_id: 'a1b2c3d4', trigger: 'download_client' },
  },
  {
    task: 'regrab',
    level: 'info',
    message: 'No outdated releases found',
    source: 'src.application.use_cases.releases.regrab_outdated',
    metadata: { component: 'regrab_outdated_releases' },
  },
];

/** Repeats the seeds over the last few hours so pagination has something to page. */
export const generateMockTaskLogs = (): RequestLogEntry[] => {
  const now = new Date();

  const logs = Array.from({ length: 6 }).flatMap((_, round) =>
    TASK_LOG_SEEDS.map((seed, index) => {
      const minutes = round * 30 + index * 2;
      const { task, metadata, ...rest } = seed;

      return buildLog(now, minutes, {
        ...rest,
        id: `task-log-${round}-${index}`,
        metadata: { ...metadata, task },
      });
    }),
  );

  logs.sort((a, b) => b.occurredAt - a.occurredAt);
  return logs;
};
