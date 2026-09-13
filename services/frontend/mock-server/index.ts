import { createHash, randomUUID } from 'crypto';
import path from 'path';

import cors from 'cors';
import express from 'express';
import morgan from 'morgan';

import { mockStore } from './store';
import type { IndexerEventType, MediaRequest, MediaType, Release } from '../src/types';

const DEFAULT_PORT = 8001;
const port = Number.parseInt(process.env.MOCK_SERVER_PORT ?? `${DEFAULT_PORT}`, 10);
const origin = process.env.MOCK_SERVER_ORIGIN ?? `http://localhost:${port}`;
const apiPath = process.env.MOCK_SERVER_API_PATH ?? '/api';
const apiBaseUrl =
  process.env.VITE_API_URL ?? process.env.REACT_APP_API_URL ?? `${origin}${apiPath}`;

const parseRequestStatus = (
  value: string | undefined | null,
): MediaRequest['status'] | undefined => {
  if (!value) return undefined;
  const allowed: MediaRequest['status'][] = [
    'pending',
    'searching',
    'downloading',
    'completed',
    'failed',
  ];
  return allowed.includes(value as MediaRequest['status'])
    ? (value as MediaRequest['status'])
    : undefined;
};

const parseReleaseStatus = (value: string | undefined | null): Release['status'] | undefined => {
  if (!value) return undefined;
  const allowed: Release['status'][] = ['pending', 'downloading', 'seeding', 'completed', 'failed'];
  return allowed.includes(value as Release['status']) ? (value as Release['status']) : undefined;
};

const fallbackId = () => Math.random().toString(36).slice(2, 12);

const generateOperationId = (operation: string) => {
  const id = typeof randomUUID === 'function' ? randomUUID() : fallbackId();
  return `${operation}-${id}`;
};

const buildAsyncResponse = (
  operation: string,
  resourceId: string,
  message: string,
  details: Record<string, unknown> | undefined = undefined,
) => {
  const operationId = generateOperationId(operation);
  const location = `${apiBaseUrl}/operations/${operationId}`;
  return {
    operation,
    status: 'queued' as const,
    operation_id: operationId,
    location,
    message,
    resource_id: resourceId,
    details,
  };
};

const app = express();
app.use(cors());
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true }));
app.use(morgan('dev'));
app.use((req, _res, next) => {
  console.log(`${req.method} ${req.originalUrl}`);
  next();
});

const contractPath = path.resolve(process.cwd(), '../../openapi.yaml');
app.get('/openapi.yaml', (_req, res, next) => {
  res.sendFile(contractPath, (err) => {
    if (err) {
      next(err);
    }
  });
});

app.get('/__health', (_req, res) => {
  res.json({ status: 'ok', apiBaseUrl });
});

const api = express.Router();

const TASK_KINDS = ['sonarr_sync', 'radarr_sync', 'release_sync', 'export', 'regrab'] as const;
type TaskKind = (typeof TASK_KINDS)[number];

const LOG_SERVICES = ['api', 'scheduler'] as const;
type LogService = (typeof LOG_SERVICES)[number];

const LOG_LEVELS = ['info', 'warning', 'error'] as const;
type LogLevel = (typeof LOG_LEVELS)[number];

const INDEXER_EVENT_TYPES = [
  'unknown',
  'indexer_query',
  'indexer_rss',
  'indexer_auth',
  'indexer_info',
  'release_grabbed',
] as const;

api.get('/requests', async (req, res) => {
  const page = Math.max(1, Number.parseInt((req.query.page as string) ?? '1', 10));
  const perPage = Math.max(1, Number.parseInt((req.query.per_page as string) ?? '20', 10));
  const status = parseRequestStatus(req.query.status as string | undefined);
  const typeParam = req.query.type as string | undefined;
  const type = typeParam === 'movie' || typeParam === 'series' ? typeParam : undefined;

  const filtered = await mockStore.listRequests({ status, type });
  const total = filtered.length;
  const start = (page - 1) * perPage;
  const paginated = filtered.slice(start, start + perPage);
  res.json({
    requests: paginated,
    total,
    page,
    per_page: perPage,
  });
});

api.post('/requests', async (req, res) => {
  const payload = req.body ?? {};
  if (!payload?.type) {
    return res.status(400).json({ message: 'Request type is required' });
  }

  try {
    const created = await mockStore.createRequest(payload);
    res.status(201).json(created);
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Invalid request payload';
    res.status(400).json({ message });
  }
});

api.get('/requests/:requestId', async (req, res) => {
  const existing = await mockStore.getRequest(req.params.requestId);
  if (!existing) {
    return res.status(404).json({ message: 'Request not found' });
  }
  res.json(existing);
});

api.patch('/requests/:requestId', async (req, res) => {
  const updated = await mockStore.updateRequest(req.params.requestId, req.body ?? {});
  if (!updated) {
    return res.status(404).json({ message: 'Request not found' });
  }
  res.json(updated);
});

api.delete('/requests/:requestId', async (req, res) => {
  const deleted = await mockStore.deleteRequest(req.params.requestId);
  if (!deleted) {
    return res.status(404).json({ message: 'Request not found' });
  }
  res.status(204).send();
});

api.get('/requests/:requestId/episodes', async (req, res) => {
  const episodes = await mockStore.listRequestEpisodes(req.params.requestId);
  if (!episodes) {
    // As with the seasons below, the mock cannot tell "no such request" from
    // "nothing to list", and the UI treats the two the same way.
    return res
      .status(409)
      .json({ code: 'seasons_unmanageable', message: 'This request has no episodes to list' });
  }
  res.json(episodes);
});

api.get('/requests/:requestId/seasons', async (req, res) => {
  const seasons = await mockStore.listRequestSeasons(req.params.requestId);
  if (!seasons) {
    // The real backend separates "no such request" from "nothing to manage";
    // the mock cannot tell them apart, and the UI treats both the same way.
    return res
      .status(409)
      .json({ code: 'seasons_unmanageable', message: 'This request has no seasons to manage' });
  }
  res.json(seasons);
});

api.put('/requests/:requestId/seasons', async (req, res) => {
  const payload = req.body ?? {};
  if (!Array.isArray(payload.season_numbers)) {
    return res.status(422).json({ message: 'season_numbers is required' });
  }

  try {
    const seasons = await mockStore.updateRequestSeasons(req.params.requestId, {
      season_numbers: payload.season_numbers,
      monitor_new_seasons: Boolean(payload.monitor_new_seasons),
    });
    if (!seasons) {
      return res
        .status(409)
        .json({ code: 'seasons_unmanageable', message: 'This request has no seasons to manage' });
    }
    res.json(seasons);
  } catch (error) {
    const code = error instanceof Error ? error.message : 'unknown';
    if (code === 'invalid_season_selection') {
      return res.status(400).json({ code, message: `Update rejected: ${code}` });
    }
    console.error('Failed to update request seasons', error);
    return res.status(500).json({ message: 'Failed to update seasons' });
  }
});

api.get('/requests/:requestId/releases', async (req, res) => {
  const page = Math.max(1, Number.parseInt((req.query.page as string) ?? '1', 10));
  const perPage = Math.max(1, Number.parseInt((req.query.per_page as string) ?? '20', 10));
  const status = parseReleaseStatus(req.query.status as string | undefined);
  const releases = await mockStore.listReleases({
    requestId: req.params.requestId,
    status,
  });
  const total = releases.length;
  const start = (page - 1) * perPage;
  const paginated = releases.slice(start, start + perPage);
  res.json({
    releases: paginated,
    total,
    page,
    per_page: perPage,
  });
});

api.get('/releases', async (req, res) => {
  const page = Math.max(1, Number.parseInt((req.query.page as string) ?? '1', 10));
  const perPage = Math.max(1, Number.parseInt((req.query.per_page as string) ?? '20', 10));
  const status = parseReleaseStatus(req.query.status as string | undefined);
  const requestId = (req.query.request_id as string | undefined) ?? undefined;
  const releases = await mockStore.listReleases({ status, requestId });
  const total = releases.length;
  const start = (page - 1) * perPage;
  const paginated = releases.slice(start, start + perPage);
  res.json({
    releases: paginated,
    total,
    page,
    per_page: perPage,
  });
});

api.post('/releases', async (req, res) => {
  try {
    const created = await mockStore.addRelease(req.body ?? {});
    res.status(201).json(created);
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Failed to create release';
    res.status(400).json({ message });
  }
});

api.get('/releases/search', async (req, res) => {
  const query = (req.query.q as string | undefined) ?? '';
  const requestId = (req.query.request_id as string | undefined) ?? undefined;
  const results = await mockStore.searchReleaseCandidates(query, requestId);
  res.json({
    results,
    query,
    total_results: results.length,
  });
});

const parseMediaType = (value: unknown): MediaType | undefined =>
  value === 'movie' || value === 'series' ? value : undefined;

api.get('/discover/search', async (req, res) => {
  const query = ((req.query.q as string | undefined) ?? '').trim();
  const rawType = req.query.type as string | undefined;
  const type = parseMediaType(rawType);
  const language = (req.query.lang as string | undefined) ?? null;
  if (!query) {
    return res.status(422).json({ message: 'Query parameter q is required' });
  }
  // An absent type searches both kinds; a type that is neither is still a bug.
  if (rawType && !type) {
    return res.status(422).json({ message: 'Query parameter type must be movie or series' });
  }

  const results = await mockStore.searchDiscoverMedia(query, type ?? null, language);
  res.json({ results });
});

api.get('/discover/series/:tvdbId/seasons', async (req, res) => {
  const tvdbId = Number.parseInt(req.params.tvdbId, 10);
  if (!Number.isInteger(tvdbId) || tvdbId < 1) {
    return res.status(422).json({ message: 'tvdbId must be a positive integer' });
  }

  const seasons = await mockStore.listDiscoverSeasons(tvdbId);
  if (!seasons) {
    return res.status(404).json({ message: 'No series matches the TVDB id' });
  }
  res.json(seasons);
});

api.get('/discover/root-folders', async (req, res) => {
  const type = parseMediaType(req.query.type);
  if (!type) {
    return res.status(422).json({ message: 'Query parameter type must be movie or series' });
  }
  res.json({ folders: await mockStore.listDiscoverRootFolders(type) });
});

api.post('/discover/requests', async (req, res) => {
  const payload = req.body ?? {};
  const type = parseMediaType(payload.type);
  const providerId = Number.parseInt(String(payload.provider_id), 10);
  if (!type || !Number.isInteger(providerId)) {
    return res.status(422).json({ message: 'type and provider_id are required' });
  }

  try {
    const requests = await mockStore.addDiscoverRequest({
      type,
      provider_id: providerId,
      root_folder_path: String(payload.root_folder_path ?? ''),
      season_numbers: Array.isArray(payload.season_numbers) ? payload.season_numbers : undefined,
      monitor_new_seasons: Boolean(payload.monitor_new_seasons),
    });
    res.status(201).json({ requests });
  } catch (error) {
    const code = error instanceof Error ? error.message : 'unknown';
    if (code === 'media_not_found') {
      return res.status(404).json({ code, message: 'No media matches the provider id' });
    }
    if (code === 'invalid_root_folder' || code === 'invalid_season_selection') {
      return res.status(400).json({ code, message: `Add rejected: ${code}` });
    }
    console.error('Failed to add discover request', error);
    return res.status(500).json({ message: 'Failed to add request' });
  }
});

api.get('/logs', async (req, res) => {
  const page = Math.max(1, Number.parseInt((req.query.page as string) ?? '1', 10));
  const perPage = Math.max(1, Number.parseInt((req.query.per_page as string) ?? '100', 10));
  const requestId = (req.query.request_id as string | undefined)?.trim();
  const task = (req.query.task as string | undefined)?.trim();
  const service = (req.query.service as string | undefined)?.trim();
  const minLevel = (req.query.min_level as string | undefined)?.trim();
  if (task && !TASK_KINDS.includes(task as TaskKind)) {
    return res.status(422).json({ message: `Unknown task: ${task}` });
  }
  if (service && !LOG_SERVICES.includes(service as LogService)) {
    return res.status(422).json({ message: `Unknown service: ${service}` });
  }
  if (minLevel && !LOG_LEVELS.includes(minLevel as LogLevel)) {
    return res.status(422).json({ message: `Unknown level: ${minLevel}` });
  }
  const logs = await mockStore.listRequestLogs({
    requestId: requestId || undefined,
    task: (task as TaskKind | undefined) || undefined,
    service: (service as LogService | undefined) || undefined,
    minLevel: (minLevel as LogLevel | undefined) || undefined,
  });
  const total = logs.length;
  const start = (page - 1) * perPage;
  const paginated = logs.slice(start, start + perPage);
  res.json({
    logs: paginated,
    total,
    page,
    per_page: perPage,
  });
});

// Declared before the release lookup below, which would otherwise treat the
// whole path as an id.
api.get('/releases/:releaseId/files/mapping/suggestions', async (req, res) => {
  const files = await mockStore.suggestedFileMappings(req.params.releaseId);
  if (!files) {
    return res.status(404).json({ message: 'Release not found' });
  }
  res.json({ files });
});

api.get('/releases/:releaseId', async (req, res) => {
  const release = await mockStore.getRelease(req.params.releaseId);
  if (!release) {
    return res.status(404).json({ message: 'Release not found' });
  }
  res.json(release);
});

api.delete('/releases/:releaseId', async (req, res) => {
  const removed = await mockStore.deleteRelease(req.params.releaseId);
  if (!removed) {
    return res.status(404).json({ message: 'Release not found' });
  }
  res.status(204).send();
});

api.post('/releases/:releaseId/pause', async (req, res) => {
  const ok = await mockStore.pauseRelease(req.params.releaseId);
  if (!ok) {
    return res.status(404).json({ message: 'Release not found' });
  }
  const body = buildAsyncResponse(
    'release.pause',
    req.params.releaseId,
    'Release pause queued (mock)',
  );
  res.status(202).location(body.location).json(body);
});

api.post('/releases/:releaseId/resume', async (req, res) => {
  const ok = await mockStore.resumeRelease(req.params.releaseId);
  if (!ok) {
    return res.status(404).json({ message: 'Release not found' });
  }
  const body = buildAsyncResponse(
    'release.resume',
    req.params.releaseId,
    'Release resume queued (mock)',
  );
  res.status(202).location(body.location).json(body);
});

api.put('/releases/:releaseId/files/mapping', async (req, res) => {
  const files = Array.isArray(req.body?.files) ? req.body.files : [];
  if (files.length === 0) {
    return res.status(400).json({ message: 'Payload must include files array' });
  }

  const success = await mockStore.updateFileMappings(req.params.releaseId, files);
  if (!success) {
    return res.status(404).json({ message: 'Release or file not found' });
  }

  res.json({ success: true });
});

api.post('/requests/:requestId/releases/download', async (req, res) => {
  const payload = req.body ?? {};
  const requestId = req.params.requestId?.trim();
  const releaseId = payload.release_id as string | undefined;
  if (!requestId || !releaseId) {
    return res.status(400).json({ message: 'requestId path param and release_id are required' });
  }

  try {
    const queued = await mockStore.queueReleaseDownload({
      requestId,
      releaseId,
    });

    const details = {
      release_id: queued.id,
      request_id: requestId,
    };
    const body = buildAsyncResponse(
      'release.download',
      queued.id,
      'Download queued (mock)',
      details,
    );
    return res.status(202).location(body.location).json(body);
  } catch (error) {
    if (error instanceof Error && error.message === 'release_candidate_not_found') {
      return res.status(404).json({
        message: 'Release candidate not found for this request',
      });
    }

    console.error('Failed to queue release download', error);
    return res.status(500).json({
      message: 'Failed to queue release download',
    });
  }
});

/**
 * The mock cannot read bencoded metadata, so an upload stands in for the info
 * hash the real backend derives from the torrent's info dict. Hashing the file
 * keeps it stable, which is what the duplicate check needs.
 */
const pseudoInfoHash = (torrentFileBase64: string): string =>
  createHash('sha1').update(Buffer.from(torrentFileBase64, 'base64')).digest('hex');

api.post('/requests/:requestId/releases/manual', async (req, res) => {
  const payload = req.body ?? {};
  const requestId = req.params.requestId?.trim();
  const magnetLink = (payload.magnet_link as string | undefined)?.trim();
  const torrentFile = (payload.torrent_file_base64 as string | undefined)?.trim();

  if (!requestId) {
    return res.status(400).json({ message: 'requestId path param is required' });
  }
  if (Boolean(magnetLink) === Boolean(torrentFile)) {
    return res
      .status(400)
      .json({ message: 'Supply exactly one of torrent_file_base64 or magnet_link' });
  }
  if (magnetLink && !magnetLink.startsWith('magnet:')) {
    return res.status(400).json({ message: 'magnet_link must be a magnet URI' });
  }

  try {
    const created = await mockStore.addRelease({
      magnet_link: magnetLink ?? `magnet:?xt=urn:btih:${pseudoInfoHash(torrentFile as string)}`,
      request_ids: [requestId],
      name: torrentFile ? 'Manual.Torrent.Upload.mock' : undefined,
      source: 'manual',
    });

    const body = buildAsyncResponse(
      'release.download',
      created.id,
      'Manual release queued (mock)',
      { release_id: created.id, request_id: requestId },
    );
    return res.status(202).location(body.location).json(body);
  } catch (error) {
    console.error('Failed to queue manual release', error);
    return res.status(500).json({ message: 'Failed to queue manual release' });
  }
});

const SYNC_ALL_SEQUENCE: TaskKind[] = [...TASK_KINDS];
const SYNC_DOWNLOADS_SEQUENCE: TaskKind[] = ['release_sync', 'export'];

const queueSync = async (
  kinds: TaskKind[],
  operation: string,
  trigger: 'api' | 'download_client',
  res: express.Response,
) => {
  const { jobs, created } = await mockStore.enqueueSyncJob({ kinds, trigger });
  // The last job finishing means the whole sequence is done.
  const tracked = jobs[jobs.length - 1];

  const body = {
    ...buildAsyncResponse(
      operation,
      tracked.id,
      created > 0 ? `${operation} queued (mock)` : 'An equivalent run is already queued.',
      {
        job_ids: jobs.map((job) => job.id),
        tasks: jobs.map((job) => job.kind),
        created,
      },
    ),
    operation_id: tracked.id,
    location: `${apiBaseUrl}/tasks/jobs/${tracked.id}`,
  };

  res.status(202).location(body.location).json(body);
};

api.post('/tasks/sync_all', async (_req, res) => {
  await queueSync(SYNC_ALL_SEQUENCE, 'sync_all', 'api', res);
});

api.post('/tasks/sync_downloads', async (_req, res) => {
  await queueSync(SYNC_DOWNLOADS_SEQUENCE, 'sync_downloads', 'download_client', res);
});

api.post('/tasks/run/:kind', async (req, res) => {
  const kind = req.params.kind as TaskKind;
  if (!TASK_KINDS.includes(kind)) {
    return res.status(422).json({ message: `Unknown task: ${kind}` });
  }
  await queueSync([kind], `run_${kind}`, 'api', res);
});

api.get('/tasks/scheduled', async (_req, res) => {
  const tasks = await mockStore.listScheduledTasks();
  res.json({ tasks });
});

api.get('/tasks/jobs', async (req, res) => {
  const limit = Math.min(
    100,
    Math.max(1, Number.parseInt((req.query.limit as string) ?? '20', 10)),
  );
  const jobs = await mockStore.listSyncJobs(limit);
  res.json({ jobs });
});

api.get('/tasks/jobs/:jobId', async (req, res) => {
  const job = await mockStore.getSyncJob(req.params.jobId);
  if (!job) {
    return res.status(404).json({ message: 'Sync job not found' });
  }
  res.json(job);
});

api.get('/indexers', async (_req, res) => {
  const indexers = await mockStore.listIndexers();
  res.json({ indexers });
});

api.get('/indexers/history', async (req, res) => {
  const page = Math.max(1, Number.parseInt((req.query.page as string) ?? '1', 10));
  const perPage = Math.min(
    100,
    Math.max(1, Number.parseInt((req.query.per_page as string) ?? '20', 10)),
  );

  const rawIndexerId = (req.query.indexer_id as string | undefined)?.trim();
  const indexerId = rawIndexerId ? Number.parseInt(rawIndexerId, 10) : undefined;
  if (indexerId !== undefined && Number.isNaN(indexerId)) {
    return res.status(422).json({ message: `Invalid indexer_id: ${rawIndexerId}` });
  }

  const rawEventType = (req.query.event_type as string | undefined)?.trim();
  if (rawEventType && !INDEXER_EVENT_TYPES.includes(rawEventType as IndexerEventType)) {
    return res.status(422).json({ message: `Unknown event type: ${rawEventType}` });
  }

  const { history, total } = await mockStore.listIndexerHistory({
    page,
    perPage,
    indexerId,
    eventType: (rawEventType as IndexerEventType | undefined) || undefined,
  });

  res.json({ history, total, page, per_page: perPage });
});

api.post('/indexers/test', async (_req, res) => {
  const results = await mockStore.testAllIndexers();
  res.json({ results });
});

api.post('/indexers/:indexerId/test', async (req, res) => {
  const indexerId = Number.parseInt(req.params.indexerId, 10);
  const result = Number.isNaN(indexerId) ? null : await mockStore.testIndexer(indexerId);
  if (!result) {
    return res.status(404).json({ code: 'indexer_not_found', message: 'Indexer not found' });
  }
  res.json(result);
});

app.use(apiPath, api);

app.use((_req, res) => {
  res.status(404).json({ message: 'Not found' });
});

app.listen(port, () => {
  console.log(`\n🔌 Mock API server ready at ${origin}`);
  console.log(`➡️  Serving routes from ${apiBaseUrl}`);
  console.log('📄 OpenAPI contract available at /openapi.yaml');
  console.log('Press Ctrl+C to stop.\n');
});
