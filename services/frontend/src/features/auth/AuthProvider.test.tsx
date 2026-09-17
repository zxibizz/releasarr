import { act, render, screen, waitFor } from '@testing-library/react';
import { StrictMode } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { AuthProvider } from '@/features/auth/AuthProvider';
import { useAuth } from '@/features/auth/useAuth';
import { setAccessToken } from '@/lib/api/client';
import { TEST_ADMIN_USER } from '@/test/utils';

function Probe() {
  const { status, user } = useAuth();
  return <div>{`${status}:${user?.username ?? 'none'}`}</div>;
}

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

const refreshCalls = () =>
  vi.mocked(fetch).mock.calls.filter(([input]) => String(input).includes('/auth/refresh'));

describe('AuthProvider bootstrap', () => {
  beforeEach(() => {
    setAccessToken(null);
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('asks for one rotation even though StrictMode mounts the provider twice', async () => {
    // Held open so both StrictMode passes get as far as the refresh before
    // either one finishes: a second request would only be visible in that
    // window, which is exactly where it used to be issued from.
    let releaseRefresh: (response: Response) => void = () => undefined;
    const refreshGate = new Promise<Response>((resolve) => {
      releaseRefresh = resolve;
    });

    vi.mocked(fetch).mockImplementation((input: RequestInfo | URL) => {
      if (String(input).includes('/auth/refresh')) {
        return refreshGate;
      }
      return Promise.resolve(jsonResponse({ required: false }));
    });

    render(
      <StrictMode>
        <AuthProvider>
          <Probe />
        </AuthProvider>
      </StrictMode>,
    );

    await waitFor(() => expect(refreshCalls()).toHaveLength(1));
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
    expect(refreshCalls()).toHaveLength(1);
    // The double mount is real, which is the whole reason this has to be shared:
    // without it both passes would ask the server to rotate the same cookie.
    expect(
      vi.mocked(fetch).mock.calls.filter(([input]) => String(input).includes('/auth/setup')),
    ).toHaveLength(2);

    releaseRefresh(jsonResponse({ access_token: 'token-1', user: TEST_ADMIN_USER }));

    await waitFor(() => expect(screen.getByText('authenticated:admin')).toBeInTheDocument());
  });

  it('reports the server as unavailable when the bootstrap refresh gets a 502', async () => {
    vi.mocked(fetch).mockImplementation((input: RequestInfo | URL) => {
      if (String(input).includes('/auth/refresh')) {
        return Promise.resolve(jsonResponse({ message: 'bad gateway' }, 502));
      }
      return Promise.resolve(jsonResponse({ required: false }));
    });

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );

    await waitFor(() => expect(screen.getByText('unavailable:none')).toBeInTheDocument());
  });

  it('reports the server as unavailable when setup-status gets a 502, without refreshing', async () => {
    vi.mocked(fetch).mockImplementation((input: RequestInfo | URL) => {
      if (String(input).includes('/auth/setup')) {
        return Promise.resolve(jsonResponse({ message: 'bad gateway' }, 502));
      }
      return Promise.resolve(jsonResponse({ access_token: 'token-1', user: TEST_ADMIN_USER }));
    });

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );

    await waitFor(() => expect(screen.getByText('unavailable:none')).toBeInTheDocument());
    expect(refreshCalls()).toHaveLength(0);
  });

  it('treats a failed refresh without a session as anonymous, not unavailable', async () => {
    vi.mocked(fetch).mockImplementation((input: RequestInfo | URL) => {
      if (String(input).includes('/auth/refresh')) {
        return Promise.resolve(jsonResponse({ message: 'no session' }, 401));
      }
      return Promise.resolve(jsonResponse({ required: false }));
    });

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );

    await waitFor(() => expect(screen.getByText('anonymous:none')).toBeInTheDocument());
  });
});
