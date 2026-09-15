import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { apiRequest, isNetworkError, setAccessToken } from '@/lib/api/client';

/** Runs a request expected to fail and hands back whatever it threw. */
async function failureOf(path: string): Promise<unknown> {
  return apiRequest(path).catch((error: unknown) => error);
}

describe('isNetworkError', () => {
  beforeEach(() => {
    setAccessToken(null);
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('recognises a request the browser could not send at all', async () => {
    vi.mocked(fetch).mockRejectedValueOnce(new TypeError('Failed to fetch'));

    expect(isNetworkError(await failureOf('/requests'))).toBe(true);
  });

  it('does not mistake a server error for a connection problem', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(new Response('', { status: 500 }));

    expect(isNetworkError(await failureOf('/requests'))).toBe(false);
  });

  it('does not mistake an aborted request for a connection problem', async () => {
    vi.mocked(fetch).mockRejectedValueOnce(new DOMException('aborted', 'AbortError'));

    expect(isNetworkError(await failureOf('/requests'))).toBe(false);
  });

  it('is false for something that was never an API error', () => {
    expect(isNetworkError(new Error('Failed to fetch'))).toBe(false);
  });
});
