import {
  getMockMappingSuggestions,
  getMockReleases,
  getMockRequests,
  searchMockReleaseSources,
} from './mockData';
import {
  DISCOVER_CATALOGUE,
  DISCOVER_ROOT_FOLDERS,
  type DiscoverCatalogueEntry,
  localizeEntry,
} from './mockDiscover';
import { generateMockIndexerHistory } from './mockIndexerHistory';
import { MOCK_FAILING_INDEXER_IDS, MOCK_INDEXERS } from './mockIndexers';
import { generateMockRequestLogs, generateMockTaskLogs } from './mockLogs';
import type {
  Indexer,
  IndexerEventType,
  IndexerHistoryEntry,
  IndexerTestResult,
  LogService,
  MediaSearchResult,
  MediaRequest,
  MediaType,
  Release,
  ReleaseFile,
  ReleaseFileMappingSuggestion,
  ReleaseSearchResult,
  ReleaseWarning,
  RequestLogEntry,
  RequestLogLevel,
  RootFolder,
  ScheduledTask,
  SeasonEpisodesResponse,
  SeasonOption,
  SeriesSeasonsResponse,
  SyncJob,
  SyncJobKind,
  SyncJobTrigger,
} from '../src/types';

type RequestStatus = MediaRequest['status'];
type RequestType = MediaRequest['type'];
type ReleaseStatus = Release['status'];

/** The same threshold the backend applies after collapsing Loguru's levels. */
const LOG_LEVEL_SEVERITY: Record<RequestLogLevel, number> = {
  info: 0,
  warning: 1,
  error: 2,
};

type EnqueueSyncJobPayload = {
  kinds: SyncJobKind[];
  trigger: SyncJobTrigger;
};

/** How long a mock job pretends to be queued, then running, before finishing. */
const MOCK_JOB_QUEUED_MS = 1_500;
const MOCK_JOB_RUNNING_MS = 4_000;

const MOCK_TASK_INTERVALS: Record<SyncJobKind, number> = {
  sonarr_sync: 3_600,
  radarr_sync: 3_600,
  release_sync: 30,
  export: 300,
  regrab: 3_600,
};

const MOCK_TASK_ORDER: SyncJobKind[] = [
  'sonarr_sync',
  'radarr_sync',
  'release_sync',
  'export',
  'regrab',
];

const MOCK_TASK_RESULTS: Record<SyncJobKind, Record<string, unknown>> = {
  sonarr_sync: { created: 0, updated: 2, completed: 1 },
  radarr_sync: { created: 1, updated: 1, completed: 0 },
  release_sync: { synced: 3, unchanged: 2, failed: 0, not_found: 0, requests_updated: 1 },
  export: { succeeded: 1, failed: 0 },
  regrab: { completed: true },
};

type NewMediaRequestPayload = {
  type: RequestType;
  title: string;
  year: number;
  poster_url?: string;
  overview?: string;
  genres?: string[];
  imdb_id?: string;
  runtime?: number;
  season_number?: number;
  total_episodes?: number;
  series_title?: string;
  series_year?: number;
};

type UpdateMediaRequestPayload = Partial<NewMediaRequestPayload> & {
  status?: RequestStatus;
};

type NewReleasePayload = {
  magnet_link: string;
  request_ids: string[];
  name?: string;
  quality?: string;
  source?: string;
};

type QueueDownloadPayload = {
  requestId: string;
  releaseId: string;
};

type UpdateFileMappingPayload = {
  file_id: string;
  request_mapping?: ReleaseFile['request_mapping'];
};

const DEFAULT_POSTER = (title: string) =>
  `https://via.placeholder.com/300x450.png?text=${encodeURIComponent(title)}`;

const clone = <T>(value: T): T => JSON.parse(JSON.stringify(value));

/**
 * Mirrors how the backend orders a search that spans both media types: the
 * closest titles first, so movies and series interleave by relevance.
 */
const titleScore = (title: string, term: string): number => {
  const candidate = title.toLowerCase();
  if (candidate === term) {
    return 0;
  }
  if (candidate.startsWith(term)) {
    return 1;
  }
  return candidate.includes(term) ? 2 : 3;
};

const randomId = () => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return Math.random().toString(36).slice(2);
};

type MappingLike = ReleaseFile['request_mapping'];

const mappingTargetKey = (mapping: MappingLike): string | null => {
  if (!mapping) return null;
  if (mapping.mapping_type === 'movie') {
    return `movie:${mapping.request_id}`;
  }
  if (mapping.season != null && mapping.episode != null) {
    return `series:${mapping.request_id}:${mapping.season}:${mapping.episode}`;
  }
  return null;
};

/**
 * Mirrors the backend's ReleaseWarningEvaluator closely enough to exercise the
 * UI: files across releases that resolve to the same request/season/episode (or
 * movie request) are flagged. Keyed on request id rather than a resolved
 * Sonarr/Radarr id, since the fixtures carry no such id.
 */
const computeMappingOverlapWarnings = (releases: Release[]): Map<string, ReleaseWarning[]> => {
  const buckets = new Map<string, Array<{ releaseId: string; fileId: string }>>();

  releases.forEach((release) => {
    release.files.forEach((file) => {
      const key = mappingTargetKey(file.request_mapping);
      if (!key) return;
      const bucket = buckets.get(key) ?? [];
      bucket.push({ releaseId: release.id, fileId: file.id });
      buckets.set(key, bucket);
    });
  });

  const fileIdsByRelease = new Map<string, Set<string>>();
  const relatedByRelease = new Map<string, Set<string>>();

  buckets.forEach((entries) => {
    if (entries.length < 2) return;
    const releaseIds = new Set(entries.map((entry) => entry.releaseId));
    entries.forEach(({ releaseId, fileId }) => {
      if (!fileIdsByRelease.has(releaseId)) fileIdsByRelease.set(releaseId, new Set());
      fileIdsByRelease.get(releaseId)!.add(fileId);
      if (!relatedByRelease.has(releaseId)) relatedByRelease.set(releaseId, new Set());
      releaseIds.forEach((id) => {
        if (id !== releaseId) relatedByRelease.get(releaseId)!.add(id);
      });
    });
  });

  const warnings = new Map<string, ReleaseWarning[]>();
  fileIdsByRelease.forEach((fileIds, releaseId) => {
    warnings.set(releaseId, [
      {
        code: 'mapping_overlap',
        file_ids: Array.from(fileIds).sort(),
        related_release_ids: Array.from(relatedByRelease.get(releaseId) ?? []).sort(),
        details: null,
      },
    ]);
  });

  return warnings;
};

export class MockStore {
  private requestsCache: MediaRequest[] | null = null;
  private releasesCache: Release[] | null = null;
  private searchResultsByRequest: Record<string, ReleaseSearchResult[]> = {};
  private requestLogsByRequestId: Record<string, RequestLogEntry[]> = {};
  private taskLogsCache: RequestLogEntry[] | null = null;
  private indexersCache: Indexer[] | null = null;
  private indexerHistoryCache: IndexerHistoryEntry[] | null = null;
  private syncJobs: SyncJob[] = [];
  // Cloned because adding media mutates it, standing in for the *arr library.
  private discoverCatalogue: DiscoverCatalogueEntry[] = DISCOVER_CATALOGUE.map((entry) =>
    clone(entry),
  );

  private async ensureRequests(): Promise<MediaRequest[]> {
    if (!this.requestsCache) {
      const requests = await getMockRequests();
      this.requestsCache = requests.map((request) => clone(request));
    }
    return this.requestsCache;
  }

  private async ensureReleases(): Promise<Release[]> {
    if (!this.releasesCache) {
      const releases = await getMockReleases();
      this.releasesCache = releases.map((release) => clone(release));
    }
    return this.releasesCache;
  }

  private async ensureRequestLogs(requestId: string): Promise<RequestLogEntry[]> {
    if (this.requestLogsByRequestId[requestId]) {
      return this.requestLogsByRequestId[requestId];
    }

    const requests = await this.ensureRequests();
    const request = requests.find((item) => item.id === requestId);
    if (!request) {
      this.requestLogsByRequestId[requestId] = [];
      return this.requestLogsByRequestId[requestId];
    }

    this.requestLogsByRequestId[requestId] = generateMockRequestLogs(request);
    return this.requestLogsByRequestId[requestId];
  }

  async listRequests(
    filters: {
      status?: RequestStatus;
      type?: RequestType;
    } = {},
  ): Promise<MediaRequest[]> {
    const { status, type } = filters;
    const requests = await this.ensureRequests();

    let result = requests;
    if (status) {
      result = result.filter((request) => request.status === status);
    }
    if (type) {
      result = result.filter((request) => request.type === type);
    }

    return result.map((request) => clone(request));
  }

  async getRequest(id: string): Promise<MediaRequest | null> {
    const requests = await this.ensureRequests();
    const request = requests.find((item) => item.id === id);
    return request ? clone(request) : null;
  }

  async createRequest(payload: NewMediaRequestPayload): Promise<MediaRequest> {
    const requests = await this.ensureRequests();

    if (payload.type === 'movie') {
      if (typeof payload.runtime !== 'number' || !payload.imdb_id) {
        throw new Error('Movie requests require runtime and imdb_id');
      }
    }

    if (payload.type === 'series') {
      if (
        typeof payload.season_number !== 'number' ||
        typeof payload.total_episodes !== 'number' ||
        !payload.series_title ||
        typeof payload.series_year !== 'number' ||
        !payload.imdb_id
      ) {
        throw new Error(
          'Series requests require season, episode counts, series metadata, and imdb_id',
        );
      }
    }

    const now = new Date().toISOString();
    const base = {
      id: randomId(),
      title: payload.title,
      year: payload.year,
      poster_url: payload.poster_url || DEFAULT_POSTER(payload.title),
      overview: payload.overview || 'No overview provided.',
      genres: payload.genres || [],
      status: 'pending' as RequestStatus,
      created_at: now,
      updated_at: now,
    };

    let request: MediaRequest;
    if (payload.type === 'movie') {
      request = {
        ...base,
        type: 'movie',
        runtime: payload.runtime!,
        imdb_id: payload.imdb_id!,
      };
    } else {
      request = {
        ...base,
        type: 'series',
        season_number: payload.season_number!,
        total_episodes: payload.total_episodes!,
        series_title: payload.series_title!,
        series_year: payload.series_year!,
        imdb_id: payload.imdb_id!,
      };
    }

    requests.unshift(request);
    return clone(request);
  }

  async updateRequest(
    id: string,
    payload: UpdateMediaRequestPayload,
  ): Promise<MediaRequest | null> {
    const requests = await this.ensureRequests();
    const request = requests.find((item) => item.id === id);
    if (!request) {
      return null;
    }

    if (payload.title) request.title = payload.title;
    if (payload.year) request.year = payload.year;
    if (payload.poster_url) request.poster_url = payload.poster_url;
    if (payload.overview) request.overview = payload.overview;
    if (payload.genres) request.genres = payload.genres;
    if (payload.status) request.status = payload.status;

    if (request.type === 'movie') {
      if (typeof payload.runtime === 'number') request.runtime = payload.runtime;
      if (payload.imdb_id) request.imdb_id = payload.imdb_id;
    } else {
      if (typeof payload.season_number === 'number') request.season_number = payload.season_number;
      if (typeof payload.total_episodes === 'number')
        request.total_episodes = payload.total_episodes;
      if (payload.series_title) request.series_title = payload.series_title;
      if (typeof payload.series_year === 'number') request.series_year = payload.series_year;
      if (payload.imdb_id) request.imdb_id = payload.imdb_id;
    }

    request.updated_at = new Date().toISOString();
    return clone(request);
  }

  /**
   * Removing a request also unmonitors what produced it, as the real endpoint
   * does. Without that the season stays wanted and the request would be rebuilt
   * the moment the catalogue was read again.
   */
  async deleteRequest(id: string): Promise<boolean> {
    const requests = await this.ensureRequests();
    const index = requests.findIndex((item) => item.id === id);
    if (index === -1) {
      return false;
    }

    const [removed] = requests.splice(index, 1);
    if (removed.type === 'series') {
      const entry = this.discoverCatalogue.find(
        (candidate) => candidate.type === 'series' && candidate.title === removed.series_title,
      );
      if (entry) {
        entry.monitored_seasons = (entry.monitored_seasons ?? []).filter(
          (season) => season !== removed.season_number,
        );
      }
    }
    return true;
  }

  async listReleases(
    filters: {
      status?: ReleaseStatus;
      requestId?: string;
    } = {},
  ): Promise<Release[]> {
    const releases = await this.ensureReleases();
    const warningsByRelease = computeMappingOverlapWarnings(releases);
    let result = releases;

    if (filters.status) {
      result = result.filter((release) => release.status === filters.status);
    }
    if (filters.requestId) {
      result = result.filter((release) => release.request_ids.includes(filters.requestId!));
    }

    return result.map((release) =>
      clone({ ...release, warnings: warningsByRelease.get(release.id) ?? [] }),
    );
  }

  async listRequestLogs(
    filters: {
      requestId?: string;
      task?: SyncJobKind;
      service?: LogService;
      minLevel?: RequestLogLevel;
    } = {},
  ): Promise<RequestLogEntry[]> {
    const { requestId, task, service, minLevel } = filters;

    if (requestId) {
      const logs = await this.ensureRequestLogs(requestId);
      return this.sortedCopy(this.select(logs, service, minLevel));
    }

    if (!this.taskLogsCache) {
      this.taskLogsCache = generateMockTaskLogs();
    }

    if (task) {
      return this.sortedCopy(
        this.select(
          this.taskLogsCache.filter((log) => log.metadata?.task === task),
          service,
          minLevel,
        ),
      );
    }

    const requests = await this.ensureRequests();
    const aggregated: RequestLogEntry[] = [...this.taskLogsCache];
    for (const req of requests) {
      aggregated.push(...(await this.ensureRequestLogs(req.id)));
    }

    return this.sortedCopy(this.select(aggregated, service, minLevel));
  }

  private select(
    logs: RequestLogEntry[],
    service: LogService | undefined,
    minLevel: RequestLogLevel | undefined,
  ): RequestLogEntry[] {
    let selected = logs;
    if (service) {
      selected = selected.filter((log) => log.metadata?.service === service);
    }
    if (minLevel) {
      // A threshold, matching the backend: warning also means error.
      const floor = LOG_LEVEL_SEVERITY[minLevel];
      selected = selected.filter((log) => LOG_LEVEL_SEVERITY[log.level] >= floor);
    }
    return selected;
  }

  private sortedCopy(logs: RequestLogEntry[]): RequestLogEntry[] {
    const copy = clone(logs) as RequestLogEntry[];
    copy.sort((a, b) => b.occurredAt - a.occurredAt);
    return copy;
  }

  async getRelease(id: string): Promise<Release | null> {
    const releases = await this.ensureReleases();
    const release = releases.find((item) => item.id === id);
    if (!release) return null;
    const warningsByRelease = computeMappingOverlapWarnings(releases);
    return clone({ ...release, warnings: warningsByRelease.get(id) ?? [] });
  }

  /** Releases already linked to a request, before a new grab decides their fate. */
  async existingReleasesFor(requestId: string): Promise<Release[]> {
    const releases = await this.ensureReleases();
    return releases
      .filter((release) => release.request_ids.includes(requestId))
      .map((release) => clone(release));
  }

  /**
   * Apply a `replace` decision: a release grabbed only for this request is
   * dropped entirely, one shared with other requests only loses this link.
   */
  async replaceExistingReleases(requestId: string, keepReleaseId: string): Promise<void> {
    const releases = await this.ensureReleases();
    for (let index = releases.length - 1; index >= 0; index -= 1) {
      const release = releases[index];
      if (release.id === keepReleaseId || !release.request_ids.includes(requestId)) {
        continue;
      }
      if (release.request_ids.length === 1) {
        releases.splice(index, 1);
      } else {
        release.request_ids = release.request_ids.filter((id) => id !== requestId);
      }
    }
  }

  async addRelease(payload: NewReleasePayload): Promise<Release> {
    const releases = await this.ensureReleases();
    const now = new Date();
    const hashFromMagnet = (() => {
      const match = payload.magnet_link.match(/btih:([^&]+)/i);
      if (match && match[1]) {
        return match[1].toLowerCase();
      }
      return randomId().replace(/-/g, '');
    })();
    const newRelease: Release = {
      id: randomId(),
      name: payload.name ?? `Manual-${now.getTime()}`,
      hash: hashFromMagnet,
      size: 0,
      files: [
        {
          id: randomId(),
          name: 'placeholder.mkv',
          size: 0,
          path: '/downloads/placeholder.mkv',
        },
      ],
      status: 'pending',
      progress: 0,
      download_speed: 0,
      upload_speed: 0,
      seeders: 0,
      leechers: 0,
      ratio: 0,
      added_date: now.toISOString(),
      request_ids: payload.request_ids,
      torrent_source: payload.source ?? 'manual',
      quality: payload.quality ?? 'unknown',
      warnings: [],
    };

    releases.unshift(newRelease);
    return clone(newRelease);
  }

  async queueReleaseDownload(payload: QueueDownloadPayload): Promise<Release> {
    const releases = await this.ensureReleases();
    const now = new Date();
    const candidates = this.searchResultsByRequest[payload.requestId] ?? [];
    const candidate = candidates.find((item) => item.release_id === payload.releaseId);

    if (!candidate) {
      throw new Error('release_candidate_not_found');
    }

    const sanitizeName = (name: string) => name.replace(/[^a-z0-9.-]+/gi, '.');
    const normalizedName = sanitizeName(candidate.release_name);
    const fallbackFileName = `${normalizedName || 'downloaded.release'}.mkv`;
    const parseSizeLabel = (label?: string): number => {
      if (!label) return 0;
      const match = label.match(/([0-9]+(?:\.[0-9]+)?)\s*(kb|mb|gb|tb)/i);
      if (!match) return 0;
      const value = Number.parseFloat(match[1]);
      const unit = match[2].toLowerCase();
      const multipliers: Record<string, number> = {
        kb: 1024,
        mb: 1024 ** 2,
        gb: 1024 ** 3,
        tb: 1024 ** 4,
      };
      return Math.floor(value * (multipliers[unit] ?? 1));
    };
    const numericSize = parseSizeLabel(candidate.size);
    const hashFromMagnet = (() => {
      if (candidate.magnet_link) {
        const match = candidate.magnet_link.match(/btih:([^&]+)/i);
        if (match && match[1]) {
          return match[1].toLowerCase();
        }
      }
      return randomId().replace(/-/g, '');
    })();

    const newRelease: Release = {
      id: candidate.release_id || randomId(),
      name: candidate.release_name,
      hash: hashFromMagnet,
      size: numericSize,
      files: [
        {
          id: randomId(),
          name: fallbackFileName,
          size: numericSize,
          path: candidate.torrent_file_url ?? `/downloads/${fallbackFileName}`,
        },
      ],
      status: 'downloading',
      progress: 1,
      download_speed: 1024 * 1024,
      upload_speed: 0,
      seeders: Math.max(10, Math.floor(Math.random() * 800)),
      leechers: Math.floor(Math.random() * 120),
      ratio: 0,
      added_date: now.toISOString(),
      request_ids: [payload.requestId],
      torrent_source: candidate.source ?? 'manual-search',
      quality: candidate.quality ?? 'unknown',
      info_url: candidate.info_url ?? null,
      published_date: candidate.publish_date ?? null,
      warnings: [],
    };

    releases.unshift(newRelease);
    return clone(newRelease);
  }

  async deleteRelease(id: string): Promise<boolean> {
    const releases = await this.ensureReleases();
    const index = releases.findIndex((item) => item.id === id);
    if (index === -1) {
      return false;
    }
    releases.splice(index, 1);
    return true;
  }

  async pauseRelease(id: string): Promise<boolean> {
    const releases = await this.ensureReleases();
    const release = releases.find((item) => item.id === id);
    if (!release) return false;
    if (release.status === 'completed') return false;
    release.status = 'pending';
    release.progress = Math.min(release.progress, 99);
    release.download_speed = 0;
    return true;
  }

  async resumeRelease(id: string): Promise<boolean> {
    const releases = await this.ensureReleases();
    const release = releases.find((item) => item.id === id);
    if (!release) return false;
    release.status = 'downloading';
    if (release.progress < 5) {
      release.progress = 5;
    }
    release.download_speed = Math.max(release.download_speed, 1024 * 1024);
    return true;
  }

  async updateFileMappings(
    releaseId: string,
    mappings: UpdateFileMappingPayload[],
  ): Promise<boolean> {
    const releases = await this.ensureReleases();
    const release = releases.find((item) => item.id === releaseId);
    if (!release) return false;
    if (!Array.isArray(mappings) || mappings.length === 0) {
      return false;
    }

    let success = true;

    mappings.forEach((mapping) => {
      const file = release.files.find((item) => item.id === mapping.file_id);
      if (!file) {
        success = false;
        return;
      }

      if (mapping.request_mapping) {
        const requestMapping = clone(mapping.request_mapping);
        if (requestMapping.mapping_type === 'movie') {
          file.request_mapping = {
            request_id: requestMapping.request_id,
            request_title: requestMapping.request_title,
            mapping_type: 'movie',
          };
        } else {
          const season =
            typeof requestMapping.season === 'number' && requestMapping.season > 0
              ? requestMapping.season
              : 1;
          const episode =
            typeof requestMapping.episode === 'number' && requestMapping.episode > 0
              ? requestMapping.episode
              : 1;
          file.request_mapping = {
            request_id: requestMapping.request_id,
            request_title: requestMapping.request_title,
            mapping_type: 'series',
            season,
            episode,
          };
        }
      }
      if (mapping.request_mapping === null) {
        file.request_mapping = undefined;
      }
    });

    return success;
  }

  async suggestedFileMappings(releaseId: string): Promise<ReleaseFileMappingSuggestion[] | null> {
    const releases = await this.ensureReleases();
    if (!releases.some((item) => item.id === releaseId)) {
      return null;
    }

    // Only offer what is not already settled, as the server does.
    const release = releases.find((item) => item.id === releaseId);
    const suggestions = (await getMockMappingSuggestions(releaseId)) ?? [];
    return suggestions.filter(
      (suggestion) =>
        !release?.files.find((file) => file.id === suggestion.file_id)?.request_mapping,
    );
  }

  async searchReleaseCandidates(query: string, requestId?: string): Promise<ReleaseSearchResult[]> {
    const results = await searchMockReleaseSources(query, requestId);
    const clonedResults = results.map((result) => clone(result));

    if (requestId) {
      this.searchResultsByRequest[requestId] = clonedResults.map((item) => clone(item));
    }

    return clonedResults;
  }

  /**
   * Mirrors the backend: a task already queued absorbs an equivalent request,
   * and jobs keep the order the caller asked for.
   */
  async enqueueSyncJob(
    payload: EnqueueSyncJobPayload,
  ): Promise<{ jobs: SyncJob[]; created: number }> {
    this.advanceSyncJobs();

    const jobs: SyncJob[] = [];
    let created = 0;

    for (const kind of payload.kinds) {
      const pending = this.syncJobs.find((job) => job.status === 'queued' && job.kind === kind);
      if (pending) {
        jobs.push(clone(pending));
        continue;
      }

      const job: SyncJob = {
        id: randomId(),
        kind,
        status: 'queued',
        trigger: payload.trigger,
        queued_at: new Date().toISOString(),
        started_at: null,
        finished_at: null,
        duration_ms: null,
        error: null,
        result: null,
      };
      this.syncJobs.unshift(job);
      jobs.push(clone(job));
      created += 1;
    }

    return { jobs, created };
  }

  async listSyncJobs(limit = 20): Promise<SyncJob[]> {
    this.advanceSyncJobs();
    return this.syncJobs.slice(0, limit).map((job) => clone(job));
  }

  async getSyncJob(id: string): Promise<SyncJob | null> {
    this.advanceSyncJobs();
    const job = this.syncJobs.find((candidate) => candidate.id === id);
    return job ? clone(job) : null;
  }

  /** Pretends the scheduler has been running each task on its interval. */
  async listScheduledTasks(): Promise<ScheduledTask[]> {
    const now = Date.now();

    return MOCK_TASK_ORDER.map((kind) => {
      const interval = MOCK_TASK_INTERVALS[kind];
      // Place the last run partway through the interval so "next execution"
      // always reads as a plausible future time.
      const lastExecution = new Date(now - interval * 1_000 * 0.4);

      return {
        kind,
        interval_seconds: interval,
        last_execution: lastExecution.toISOString(),
        last_duration_ms: 200 + MOCK_TASK_ORDER.indexOf(kind) * 350,
        last_status: 'completed',
        last_error: null,
        next_execution: new Date(lastExecution.getTime() + interval * 1_000).toISOString(),
      } satisfies ScheduledTask;
    });
  }

  async listIndexers(): Promise<Indexer[]> {
    return this.ensureIndexers().map((indexer) => clone(indexer));
  }

  /** Prowlarr paginates its history server-side, so the page is sliced here. */
  async listIndexerHistory(filters: {
    page: number;
    perPage: number;
    indexerId?: number;
    eventType?: IndexerEventType;
  }): Promise<{ history: IndexerHistoryEntry[]; total: number }> {
    if (this.indexerHistoryCache === null) {
      this.indexerHistoryCache = generateMockIndexerHistory();
    }

    const matches = this.indexerHistoryCache.filter(
      (entry) =>
        (filters.indexerId === undefined || entry.indexer_id === filters.indexerId) &&
        (filters.eventType === undefined || entry.event_type === filters.eventType),
    );

    const start = (filters.page - 1) * filters.perPage;
    return {
      history: matches.slice(start, start + filters.perPage).map((entry) => clone(entry)),
      total: matches.length,
    };
  }

  /**
   * Runs a mock test, mirroring the real effect of a passing one: Prowlarr
   * clears its back-off, so the indexer stops being blocked.
   */
  async testIndexer(id: number): Promise<IndexerTestResult | null> {
    const indexer = this.ensureIndexers().find((candidate) => candidate.id === id);
    if (!indexer) {
      return null;
    }
    return this.runIndexerTest(indexer);
  }

  /** Prowlarr only tests indexers that are switched on. */
  async testAllIndexers(): Promise<IndexerTestResult[]> {
    return this.ensureIndexers()
      .filter((indexer) => indexer.enabled)
      .map((indexer) => this.runIndexerTest(indexer));
  }

  private runIndexerTest(indexer: Indexer): IndexerTestResult {
    if (MOCK_FAILING_INDEXER_IDS.has(indexer.id)) {
      return {
        indexer_id: indexer.id,
        name: indexer.name,
        success: false,
        errors: ['Unable to connect to indexer'],
      };
    }

    indexer.disabled_till = null;
    indexer.most_recent_failure = null;
    indexer.initial_failure = null;
    indexer.health = indexer.enabled ? 'healthy' : 'disabled';

    return { indexer_id: indexer.id, name: indexer.name, success: true, errors: [] };
  }

  private ensureIndexers(): Indexer[] {
    if (this.indexersCache === null) {
      this.indexersCache = MOCK_INDEXERS.map((indexer) => clone(indexer));
    }
    return this.indexersCache;
  }

  /** A null type searches both kinds, as the real endpoint does. */
  async searchDiscoverMedia(
    query: string,
    type: MediaType | null,
    language?: string | null,
  ): Promise<MediaSearchResult[]> {
    const term = query.trim().toLowerCase();
    if (!term) {
      return [];
    }

    const requests = await this.ensureRequests();
    return this.discoverCatalogue
      .filter((entry) => type === null || entry.type === type)
      .map((entry) => ({ entry, localized: localizeEntry(entry, language) }))
      .filter(
        ({ entry, localized }) =>
          entry.title.toLowerCase().includes(term) || localized.title.toLowerCase().includes(term),
      )
      .map(({ entry, localized }) => {
        const related = this.requestsForEntry(requests, entry);
        const seasons = related
          .map((request) => (request.type === 'series' ? request.season_number : null))
          .filter((season): season is number => season !== null)
          .sort((a, b) => a - b);

        return {
          type: entry.type,
          provider_id: entry.provider_id,
          title: localized.title,
          year: entry.year,
          overview: localized.overview,
          poster_url: entry.poster_url,
          in_library: entry.library_id !== undefined,
          library_id: entry.library_id ?? null,
          requested_seasons: seasons,
          request_id: entry.type === 'movie' ? (related[0]?.id ?? null) : null,
          request_status: entry.type === 'movie' ? (related[0]?.status ?? null) : null,
        } satisfies MediaSearchResult;
      })
      .sort((a, b) => titleScore(a.title, term) - titleScore(b.title, term));
  }

  async listDiscoverSeasons(tvdbId: number): Promise<SeriesSeasonsResponse | null> {
    const entry = this.discoverCatalogue.find(
      (candidate) => candidate.type === 'series' && candidate.provider_id === tvdbId,
    );
    return entry ? await this.describeSeasons(entry) : null;
  }

  /**
   * The episodes of the season a request covers, made up from its episode count.
   *
   * Air dates are laid out weekly so that the last two of any season are still
   * to come, and every fourth aired episode is left without a file: between
   * them the three states a row can be in all show up on one page.
   */
  async listRequestEpisodes(requestId: string): Promise<SeasonEpisodesResponse | null> {
    const request = await this.getRequest(requestId);
    if (!request || request.type !== 'series') {
      return null;
    }

    const total = Math.max(0, request.total_episodes);
    const week = 7 * 24 * 60 * 60 * 1000;
    const now = Date.now();

    return {
      season_number: request.season_number,
      episodes: Array.from({ length: total }, (_, index) => {
        const number = index + 1;
        const airDate = new Date(now - (total - 2 - number) * week);
        const aired = airDate.getTime() <= now;
        const hasFile = aired && number % 4 !== 0;
        return {
          episode_number: number,
          title: `Episode ${number}`,
          status: hasFile ? 'downloaded' : aired ? 'missing' : 'unaired',
          air_date: airDate.toISOString(),
          // Around 2 GB an episode, varied a little so the column is not a
          // stack of identical numbers.
          file_size: hasFile ? 1_900_000_000 + number * 37_000_000 : null,
        };
      }),
    };
  }

  /** The seasons of the series a request belongs to, for managing the selection. */
  async listRequestSeasons(requestId: string): Promise<SeriesSeasonsResponse | null> {
    const entry = await this.entryForRequest(requestId);
    return entry ? await this.describeRequestSeasons(entry) : null;
  }

  /**
   * Brings the monitoring of a series in line with the selection. The selection
   * is Sonarr's monitoring, so the difference is taken against the seasons
   * monitored now rather than against the requests: a season already monitored
   * keeps whatever request state it had, and one left out is unmonitored with
   * its request removed.
   */
  async updateRequestSeasons(
    requestId: string,
    payload: { season_numbers: number[]; monitor_new_seasons?: boolean },
  ): Promise<SeriesSeasonsResponse | null> {
    const entry = await this.entryForRequest(requestId);
    if (!entry) {
      return null;
    }

    const desired = [...new Set(payload.season_numbers)].filter((season) => season > 0);
    const known = entry.seasons ?? [];
    if (known.length > 0 && desired.some((season) => !known.includes(season))) {
      throw new Error('invalid_season_selection');
    }

    const monitoredNow = (entry.monitored_seasons ?? []).filter((season) => season > 0);
    const added = desired.filter((season) => !monitoredNow.includes(season));
    const removed = monitoredNow.filter((season) => !desired.includes(season));

    const requests = await this.ensureRequests();
    const related = this.requestsForEntry(requests, entry).filter(
      (request) => request.type === 'series',
    );

    for (const request of related) {
      const season = (request as { season_number: number }).season_number;
      if (removed.includes(season)) {
        await this.deleteRequest(request.id);
      }
    }

    // A dropped season with no request of its own still has to come off the
    // monitored list, which only the request deletion above would have done.
    entry.monitored_seasons = (entry.monitored_seasons ?? []).filter(
      (season) => !removed.includes(season),
    );

    for (const season of added) {
      await this.addDiscoverRequest({
        type: 'series',
        provider_id: entry.provider_id,
        // A series being managed is in the library already, so Sonarr owns its
        // path; the add ignores the one sent for it and only needs it valid.
        root_folder_path: DISCOVER_ROOT_FOLDERS.series[0]?.path ?? '',
        season_numbers: [season],
      });
    }

    entry.monitor_new_seasons = payload.monitor_new_seasons ?? false;
    // Described from the series rather than the request, which may be one of
    // the rows just deleted - as it is whenever its own season was dropped.
    return await this.describeRequestSeasons(entry);
  }

  /** The seasons as the request-scoped endpoint reports them, without a TVDB id. */
  private async describeRequestSeasons(
    entry: DiscoverCatalogueEntry,
  ): Promise<SeriesSeasonsResponse> {
    return { ...(await this.describeSeasons(entry)), tvdb_id: null };
  }

  private async describeSeasons(entry: DiscoverCatalogueEntry): Promise<SeriesSeasonsResponse> {
    const requests = await this.ensureRequests();
    const requestBySeason = new Map(
      this.requestsForEntry(requests, entry)
        .filter((request) => request.type === 'series')
        .map((request) => [(request as { season_number: number }).season_number, request.id]),
    );

    return {
      tvdb_id: entry.provider_id,
      in_library: entry.library_id !== undefined,
      library_id: entry.library_id ?? null,
      monitor_new_seasons: entry.monitor_new_seasons ?? false,
      seasons: (entry.seasons ?? []).map(
        (seasonNumber) =>
          ({
            season_number: seasonNumber,
            monitored: (entry.monitored_seasons ?? []).includes(seasonNumber),
            requested: requestBySeason.has(seasonNumber),
            downloaded: (entry.downloaded_seasons ?? []).includes(seasonNumber),
            request_id: requestBySeason.get(seasonNumber) ?? null,
          }) satisfies SeasonOption,
      ),
    };
  }

  /**
   * The series a request belongs to, or nothing when the request is a movie or
   * the catalogue has no series under that title.
   */
  private async entryForRequest(requestId: string): Promise<DiscoverCatalogueEntry | null> {
    const requests = await this.ensureRequests();
    const request = requests.find((candidate) => candidate.id === requestId);
    if (!request || request.type !== 'series') {
      return null;
    }
    return (
      this.discoverCatalogue.find(
        (candidate) => candidate.type === 'series' && candidate.title === request.series_title,
      ) ?? null
    );
  }

  async listDiscoverRootFolders(type: MediaType): Promise<RootFolder[]> {
    return DISCOVER_ROOT_FOLDERS[type].map((folder) => clone(folder));
  }

  /**
   * Adds the picked media and returns the resulting requests, mirroring the real
   * endpoint: the rows exist by the time this resolves, and media already in the
   * library is monitored rather than re-added.
   */
  async addDiscoverRequest(payload: {
    type: MediaType;
    provider_id: number;
    root_folder_path: string;
    season_numbers?: number[];
    monitor_new_seasons?: boolean;
  }): Promise<MediaRequest[]> {
    const entry = this.discoverCatalogue.find(
      (candidate) =>
        candidate.type === payload.type && candidate.provider_id === payload.provider_id,
    );
    if (!entry) {
      throw new Error('media_not_found');
    }

    const alreadyInLibrary = entry.library_id !== undefined;
    if (!alreadyInLibrary) {
      const folders = DISCOVER_ROOT_FOLDERS[payload.type];
      if (!folders.some((folder) => folder.path === payload.root_folder_path)) {
        throw new Error('invalid_root_folder');
      }
      entry.library_id = 900 + this.discoverCatalogue.indexOf(entry);
    }

    if (payload.type === 'movie') {
      if (payload.season_numbers?.length) {
        throw new Error('invalid_season_selection');
      }
      const requests = await this.ensureRequests();
      const existing = this.requestsForEntry(requests, entry)[0];
      if (existing) {
        return [clone(existing)];
      }
      const created = await this.createRequest({
        type: 'movie',
        title: entry.title,
        year: entry.year,
        overview: entry.overview,
        poster_url: entry.poster_url ?? undefined,
        runtime: 120,
        imdb_id: `tt${entry.provider_id}`,
      });
      return [created];
    }

    const seasons = [...new Set(payload.season_numbers ?? [])].sort((a, b) => a - b);
    // An added series takes an empty selection as a request for nothing, which
    // is how one Sonarr already covers in full still gets its new-seasons flag
    // set. Adding the series itself needs a season to monitor.
    if (seasons.length === 0 && !alreadyInLibrary) {
      throw new Error('invalid_season_selection');
    }
    const known = entry.seasons ?? [];
    if (known.length > 0 && seasons.some((season) => !known.includes(season))) {
      throw new Error('invalid_season_selection');
    }

    entry.monitored_seasons = [...new Set([...(entry.monitored_seasons ?? []), ...seasons])];
    if (payload.monitor_new_seasons !== undefined) {
      entry.monitor_new_seasons = payload.monitor_new_seasons;
    }

    const created: MediaRequest[] = [];
    for (const seasonNumber of seasons) {
      const requests = await this.ensureRequests();
      const existing = this.requestsForEntry(requests, entry).find(
        (request) => request.type === 'series' && request.season_number === seasonNumber,
      );
      created.push(
        existing
          ? clone(existing)
          : await this.createRequest({
              type: 'series',
              title:
                seasonNumber <= 0
                  ? `${entry.title} - Specials`
                  : `${entry.title} - Season ${seasonNumber}`,
              year: entry.year,
              overview: entry.overview,
              poster_url: entry.poster_url ?? undefined,
              season_number: seasonNumber,
              total_episodes: 10,
              series_title: entry.title,
              series_year: entry.year,
              imdb_id: `tt${entry.provider_id}`,
            }),
      );
    }
    return created;
  }

  /**
   * The real backend joins requests to media on the Sonarr/Radarr id; the mock
   * data carries no such ids, so the title stands in for one.
   */
  private requestsForEntry(
    requests: MediaRequest[],
    entry: DiscoverCatalogueEntry,
  ): MediaRequest[] {
    return requests.filter((request) =>
      request.type === 'series'
        ? entry.type === 'series' && request.series_title === entry.title
        : entry.type === 'movie' && request.title === entry.title,
    );
  }

  /** Moves jobs through queued → running → completed based on elapsed time. */
  private advanceSyncJobs(): void {
    const now = Date.now();

    for (const job of this.syncJobs) {
      const queuedAt = new Date(job.queued_at).getTime();

      if (job.status === 'queued' && now - queuedAt >= MOCK_JOB_QUEUED_MS) {
        job.status = 'running';
        job.started_at = new Date(queuedAt + MOCK_JOB_QUEUED_MS).toISOString();
      }

      if (job.status === 'running') {
        const startedAt = new Date(job.started_at ?? job.queued_at).getTime();
        if (now - startedAt >= MOCK_JOB_RUNNING_MS) {
          job.status = 'completed';
          job.finished_at = new Date(startedAt + MOCK_JOB_RUNNING_MS).toISOString();
          job.duration_ms = MOCK_JOB_RUNNING_MS;
          job.result = MOCK_TASK_RESULTS[job.kind];
        }
      }
    }
  }
}

export const mockStore = new MockStore();
