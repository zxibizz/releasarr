import { http, HttpResponse } from 'msw';
import { mockStore } from './store';
import type { MediaRequest, Release } from '../types';

const API_BASE = (process.env.REACT_APP_API_URL ?? 'http://localhost:8001/api').replace(/\/$/, '');

const withStatusFilter = (value: string | null): MediaRequest['status'] | undefined => {
  if (!value) return undefined;
  const allowed: MediaRequest['status'][] = ['pending', 'searching', 'downloading', 'completed', 'failed'];
  return allowed.includes(value as MediaRequest['status']) ? (value as MediaRequest['status']) : undefined;
};

const withReleaseStatus = (value: string | null): Release['status'] | undefined => {
  if (!value) return undefined;
  const allowed: Release['status'][] = ['pending', 'downloading', 'seeding', 'completed', 'failed'];
  return allowed.includes(value as Release['status']) ? (value as Release['status']) : undefined;
};

export const handlers = [
  http.get(`${API_BASE}/requests`, async ({ request }) => {
    const url = new URL(request.url);
    const page = Math.max(1, parseInt(url.searchParams.get('page') ?? '1', 10));
    const perPage = Math.max(1, parseInt(url.searchParams.get('per_page') ?? '20', 10));
    const status = withStatusFilter(url.searchParams.get('status'));
    const typeParam = url.searchParams.get('type');
    const type = typeParam === 'movie' || typeParam === 'series' ? typeParam : undefined;

    const filtered = await mockStore.listRequests({ status, type });
    const total = filtered.length;
    const start = (page - 1) * perPage;
    const paginated = filtered.slice(start, start + perPage);

    return HttpResponse.json({
      requests: paginated,
      total,
      page,
      per_page: perPage,
    });
  }),

  http.post(`${API_BASE}/requests`, async ({ request }) => {
    try {
      const payload = (await request.json()) as Partial<MediaRequest> & { type?: string };
      if (!payload?.type) {
        return HttpResponse.json({ message: 'Request type is required' }, { status: 400 });
      }
      const created = await mockStore.createRequest(payload as any);
      return HttpResponse.json(created, { status: 201 });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Invalid request payload';
      return HttpResponse.json({ message }, { status: 400 });
    }
  }),

  http.get(`${API_BASE}/requests/:requestId`, async ({ params }) => {
    const requestData = await mockStore.getRequest(params.requestId as string);
    if (!requestData) {
      return HttpResponse.json({ message: 'Request not found' }, { status: 404 });
    }
    return HttpResponse.json(requestData);
  }),

  http.put(`${API_BASE}/requests/:requestId`, async ({ params, request }) => {
    const payload = (await request.json()) as Partial<MediaRequest>;
    const updated = await mockStore.updateRequest(params.requestId as string, payload as any);
    if (!updated) {
      return HttpResponse.json({ message: 'Request not found' }, { status: 404 });
    }
    return HttpResponse.json(updated);
  }),

  http.delete(`${API_BASE}/requests/:requestId`, async ({ params }) => {
    const deleted = await mockStore.deleteRequest(params.requestId as string);
    if (!deleted) {
      return HttpResponse.json({ message: 'Request not found' }, { status: 404 });
    }
    return new HttpResponse(null, { status: 204 });
  }),

  http.get(`${API_BASE}/requests/:requestId/releases`, async ({ params }) => {
    const releases = await mockStore.listReleases({ requestId: params.requestId as string });
    return HttpResponse.json(releases);
  }),

  http.get(`${API_BASE}/releases`, async ({ request }) => {
    const url = new URL(request.url);
    const status = withReleaseStatus(url.searchParams.get('status'));
    const requestId = url.searchParams.get('request_id') ?? undefined;
    const releases = await mockStore.listReleases({ status, requestId });
    return HttpResponse.json(releases);
  }),

  http.post(`${API_BASE}/releases`, async ({ request }) => {
    try {
      const payload = (await request.json()) as any;
      const created = await mockStore.addRelease(payload);
      return HttpResponse.json(created, { status: 201 });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to create release';
      return HttpResponse.json({ message }, { status: 400 });
    }
  }),

  http.get(`${API_BASE}/releases/:releaseId`, async ({ params }) => {
    const release = await mockStore.getRelease(params.releaseId as string);
    if (!release) {
      return HttpResponse.json({ message: 'Release not found' }, { status: 404 });
    }
    return HttpResponse.json(release);
  }),

  http.delete(`${API_BASE}/releases/:releaseId`, async ({ params }) => {
    const deleted = await mockStore.deleteRelease(params.releaseId as string);
    if (!deleted) {
      return HttpResponse.json({ message: 'Release not found' }, { status: 404 });
    }
    return new HttpResponse(null, { status: 204 });
  }),

  http.post(`${API_BASE}/releases/:releaseId/pause`, async ({ params }) => {
    const ok = await mockStore.pauseRelease(params.releaseId as string);
    if (!ok) {
      return HttpResponse.json({ message: 'Release not found' }, { status: 404 });
    }
    return new HttpResponse(null, { status: 202 });
  }),

  http.post(`${API_BASE}/releases/:releaseId/resume`, async ({ params }) => {
    const ok = await mockStore.resumeRelease(params.releaseId as string);
    if (!ok) {
      return HttpResponse.json({ message: 'Release not found' }, { status: 404 });
    }
    return new HttpResponse(null, { status: 202 });
  }),

  http.put(`${API_BASE}/releases/:releaseId/files/mapping`, async ({ params, request }) => {
    const payload = (await request.json()) as { files?: any[] };
    const success = await mockStore.updateFileMappings(
      params.releaseId as string,
      payload?.files ?? [],
    );
    if (!success) {
      return HttpResponse.json({ message: 'Release or file not found' }, { status: 404 });
    }
    return HttpResponse.json({ success: true });
  }),

  http.get(`${API_BASE}/releases/stats`, async () => {
    const stats = await mockStore.getReleaseStats();
    return HttpResponse.json(stats);
  }),

  http.get(`${API_BASE}/releases/search`, async ({ request }) => {
    const url = new URL(request.url);
    const query = url.searchParams.get('q') ?? '';
    const results = await mockStore.searchReleaseCandidates(query);
    return HttpResponse.json({
      results,
      query,
      total_results: results.length,
    });
  }),

  http.post(`${API_BASE}/releases/download`, async () => {
    return HttpResponse.json({ message: 'Download queued (mock)' }, { status: 202 });
  }),
];
