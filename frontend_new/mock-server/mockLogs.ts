import type { MediaRequest } from '../src/types';
import type { RequestLogEntry } from '../src/types/logs';

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
    occurredAt: occurredAtDate.getTime(),
    timestamp: formatTimestamp(occurredAtDate),
    ...entry,
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
