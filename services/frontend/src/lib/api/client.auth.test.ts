import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  SESSION_EXPIRED_MESSAGE,
  apiRequest,
  getAccessToken,
  onAuthExpired,
  refreshSession,
  setAccessToken,
} from '@/lib/api/client';

function jsonResponse(body: unknown, init: { status?: number } = {}) {
  return new Response(JSON.stringify(body), {
    status: init.status ?? 200,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('apiRequest auth handling', () => {
  beforeEach(() => {
    setAccessToken(null);
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('attaches the access token as a bearer header when one is set', async () => {
    setAccessToken('token-123');
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ ok: true }));

    await apiRequest('/requests');

    const [, init] = vi.mocked(fetch).mock.calls[0];
    const headers = init?.headers as Headers;
    expect(headers.get('Authorization')).toBe('Bearer token-123');
  });

  it('refreshes once and retries after a 401, then keeps the new token', async () => {
    setAccessToken('stale-token');
    vi.mocked(fetch)
      .mockResolvedValueOnce(jsonResponse({ code: 'unauthorized' }, { status: 401 }))
      .mockResolvedValueOnce(jsonResponse({ access_token: 'fresh-token', user: { id: 'u1' } }))
      .mockResolvedValueOnce(jsonResponse({ requests: [] }));

    const result = await apiRequest('/requests');

    expect(result).toEqual({ requests: [] });
    expect(getAccessToken()).toBe('fresh-token');
    expect(vi.mocked(fetch)).toHaveBeenCalledTimes(3);
    expect(vi.mocked(fetch).mock.calls[1][0]).toContain('/auth/refresh');
  });

  it('shares a single refresh call across concurrent 401s', async () => {
    setAccessToken('stale-token');
    vi.mocked(fetch).mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes('/auth/refresh')) {
        return Promise.resolve(jsonResponse({ access_token: 'fresh-token', user: { id: 'u1' } }));
      }
      if (getAccessToken() === 'stale-token') {
        return Promise.resolve(jsonResponse({ code: 'unauthorized' }, { status: 401 }));
      }
      return Promise.resolve(jsonResponse({ ok: true }));
    });

    await Promise.all([apiRequest('/requests'), apiRequest('/releases')]);

    const refreshCalls = vi
      .mocked(fetch)
      .mock.calls.filter(([input]) => String(input).includes('/auth/refresh'));
    expect(refreshCalls).toHaveLength(1);
  });

  it('clears the token and notifies subscribers when the refresh itself fails', async () => {
    setAccessToken('stale-token');
    vi.mocked(fetch)
      .mockResolvedValueOnce(jsonResponse({ code: 'unauthorized' }, { status: 401 }))
      .mockResolvedValueOnce(jsonResponse({ code: 'invalid_refresh_token' }, { status: 401 }));

    const listener = vi.fn();
    const unsubscribe = onAuthExpired(listener);

    await expect(apiRequest('/requests')).rejects.toThrow();

    expect(getAccessToken()).toBeNull();
    expect(listener).toHaveBeenCalledTimes(1);
    unsubscribe();
  });

  it('reports a session it cannot restore as expired, not as a bad access token', async () => {
    setAccessToken('stale-token');
    vi.mocked(fetch)
      .mockResolvedValueOnce(
        jsonResponse(
          { code: 'invalid_token', message: 'Access token is invalid or expired' },
          { status: 401 },
        ),
      )
      .mockResolvedValueOnce(jsonResponse({ code: 'invalid_refresh_token' }, { status: 401 }));

    const error = await apiRequest('/requests').catch((reason: unknown) => reason);

    // The caller is being sent to the login page; naming the access token there
    // only tells the user about internals they cannot act on.
    expect(error).toBeInstanceOf(Error);
    expect((error as Error).message).toBe(SESSION_EXPIRED_MESSAGE);
    expect((error as { status?: number }).status).toBe(401);
  });

  it('shares one refresh between the bootstrap and a request that 401s alongside it', async () => {
    let releaseRefresh: (response: Response) => void = () => undefined;
    const refreshGate = new Promise<Response>((resolve) => {
      releaseRefresh = resolve;
    });

    vi.mocked(fetch).mockImplementation((input: RequestInfo | URL) => {
      if (String(input).includes('/auth/refresh')) {
        return refreshGate;
      }
      // Anything sent before the session is restored carries no token.
      if (getAccessToken() === null) {
        return Promise.resolve(jsonResponse({ code: 'unauthorized' }, { status: 401 }));
      }
      return Promise.resolve(jsonResponse({ ok: true }));
    });

    const bootstrap = refreshSession();
    const request = apiRequest('/requests');
    releaseRefresh(jsonResponse({ access_token: 'fresh-token', user: { id: 'u1' } }));

    await expect(bootstrap).resolves.toMatchObject({ access_token: 'fresh-token' });
    await expect(request).resolves.toEqual({ ok: true });

    const refreshCalls = vi
      .mocked(fetch)
      .mock.calls.filter(([input]) => String(input).includes('/auth/refresh'));
    expect(refreshCalls).toHaveLength(1);
  });

  it('never attempts a refresh for the auth endpoints themselves', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({ code: 'invalid_credentials' }, { status: 401 }),
    );

    await expect(apiRequest('/auth/login', { method: 'POST', body: {} })).rejects.toThrow();

    expect(vi.mocked(fetch)).toHaveBeenCalledTimes(1);
  });
});
