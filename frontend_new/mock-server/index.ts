import cors from 'cors';
import express from 'express';
import morgan from 'morgan';
import path from 'path';
import type { MediaRequest, Release } from '../src/types';
import { mockStore } from './store';

const DEFAULT_PORT = 8001;
const port = Number.parseInt(process.env.MOCK_SERVER_PORT ?? `${DEFAULT_PORT}`, 10);
const origin = process.env.MOCK_SERVER_ORIGIN ?? `http://localhost:${port}`;
const apiPath = process.env.MOCK_SERVER_API_PATH ?? '/api';
const apiBaseUrl = process.env.REACT_APP_API_URL ?? `${origin}${apiPath}`;

const parseRequestStatus = (value: string | undefined | null): MediaRequest['status'] | undefined => {
  if (!value) return undefined;
  const allowed: MediaRequest['status'][] = ['pending', 'searching', 'downloading', 'completed', 'failed'];
  return allowed.includes(value as MediaRequest['status']) ? (value as MediaRequest['status']) : undefined;
};

const parseReleaseStatus = (value: string | undefined | null): Release['status'] | undefined => {
  if (!value) return undefined;
  const allowed: Release['status'][] = ['pending', 'downloading', 'seeding', 'completed', 'failed'];
  return allowed.includes(value as Release['status']) ? (value as Release['status']) : undefined;
};

const app = express();
app.use(cors());
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true }));
app.use(morgan('dev'));
app.use((req, _res, next) => {
  console.log(`[mock] ${req.method} ${req.originalUrl}`);
  next();
});

const contractPath = path.resolve(process.cwd(), '../openapi.yaml');
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

api.put('/requests/:requestId', async (req, res) => {
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

api.get('/requests/:requestId/releases', async (req, res) => {
  const releases = await mockStore.listReleases({ requestId: req.params.requestId });
  res.json(releases);
});

api.get('/releases', async (req, res) => {
  const status = parseReleaseStatus(req.query.status as string | undefined);
  const requestId = (req.query.request_id as string | undefined) ?? undefined;
  const releases = await mockStore.listReleases({ status, requestId });
  res.json(releases);
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
  res.status(202).send();
});

api.post('/releases/:releaseId/resume', async (req, res) => {
  const ok = await mockStore.resumeRelease(req.params.releaseId);
  if (!ok) {
    return res.status(404).json({ message: 'Release not found' });
  }
  res.status(202).send();
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

    return res
      .status(202)
      .json({ message: 'Download queued (mock)', release: queued });
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
