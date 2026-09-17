import type { LoginResponse } from '@/types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001/api';

const STATUS_MESSAGES: Record<number, string> = {
  400: 'The request was invalid. Please check the data and try again.',
  401: 'Authentication is required to complete this action.',
  403: 'You do not have permission to complete this action.',
  404: 'The requested resource could not be found.',
  409: 'A conflict prevented this action from completing.',
  422: 'The server could not process the provided data.',
  429: 'Too many requests — please wait before trying again.',
  500: 'The server encountered an error. Please try again later.',
  502: 'Bad gateway — the upstream service returned an invalid response.',
  503: 'The service is temporarily unavailable. Please try again soon.',
  504: 'The service timed out while processing the request.',
};

const statusMessage = (status: number): string => {
  if (STATUS_MESSAGES[status]) {
    return STATUS_MESSAGES[status];
  }
  if (status >= 500) {
    return 'A server error occurred. Please try again later.';
  }
  if (status >= 400) {
    return 'The server could not process the request. Please verify the input and retry.';
  }
  return `Request failed with status ${status}`;
};

export class ApiError extends Error {
  readonly status?: number;
  readonly details?: unknown;

  constructor(
    message: string,
    options: { status?: number; details?: unknown; cause?: unknown } = {},
  ) {
    super(message, { cause: options.cause });
    this.name = 'ApiError';
    this.status = options.status;
    this.details = options.details;
  }
}

/**
 * True when the request never reached the server at all. `fetch` rejects with a
 * `TypeError` for that and for nothing else here, which is what separates "no
 * connection" from the 4xx and 5xx failures that always carry a status.
 */
export function isNetworkError(error: unknown): boolean {
  return error instanceof ApiError && error.cause instanceof TypeError;
}

/**
 * True when the server answered but said it cannot serve (5xx). The auth
 * bootstrap uses this to tell "backend down" apart from "no session", which
 * the refresh call's `null` alone cannot express.
 */
export function isServerUnavailable(error: unknown): boolean {
  return error instanceof ApiError && error.status !== undefined && error.status >= 500;
}

type QueryValue = string | number | boolean | undefined | null;

export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE';
  body?: unknown;
  query?: Record<string, QueryValue>;
  signal?: AbortSignal;
}

const buildUrl = (path: string, query?: Record<string, QueryValue>): string => {
  const search = new URLSearchParams();
  Object.entries(query ?? {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      search.set(key, String(value));
    }
  });
  const queryString = search.toString();
  return `${API_BASE_URL}${path}${queryString ? `?${queryString}` : ''}`;
};

// The access token lives in memory only, never in storage — an XSS payload can
// still steal it for as long as the tab is open, but not after a reload, and
// it never survives to be read back out of localStorage.
let accessToken: string | null = null;

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function getAccessToken(): string | null {
  return accessToken;
}

type AuthExpiredListener = () => void;
const authExpiredListeners = new Set<AuthExpiredListener>();

/** Subscribes to "the session could not be restored"; returns an unsubscribe function. */
export function onAuthExpired(listener: AuthExpiredListener): () => void {
  authExpiredListeners.add(listener);
  return () => authExpiredListeners.delete(listener);
}

// These endpoints must never trigger a refresh attempt themselves, or a wrong
// password would recurse into a second login call instead of just failing.
const NEVER_REFRESH_PATHS = ['/auth/login', '/auth/refresh', '/auth/setup', '/auth/logout'];

const isAuthPath = (path: string): boolean =>
  NEVER_REFRESH_PATHS.some((prefix) => path.startsWith(prefix));

/**
 * Shown when a request 401s and the session behind it cannot be restored. The
 * backend's own message names the access token, which is an implementation
 * detail the user cannot act on and is about to be sent to the login page.
 */
export const SESSION_EXPIRED_MESSAGE = 'Your session has expired. Please sign in again.';

// Several requests can 401 at once, and every tab shares the one refresh cookie
// in the jar. Both the app's bootstrap and the retries below go through this
// single in-flight call, so a rotation the server performs exactly once is
// never requested twice — a second request would carry a token the first has
// already rotated away.
let refreshInFlight: Promise<LoginResponse | null> | null = null;

/** Restore the session from the refresh cookie, or `null` when there is none. */
export function refreshSession(): Promise<LoginResponse | null> {
  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
          method: 'POST',
          credentials: 'include',
          headers: { Accept: 'application/json' },
        });
        if (!response.ok) {
          // A 5xx is the server failing, not the session being absent. Throwing
          // lets the bootstrap say "unavailable" instead of redirecting to a
          // login form that would fail the same way.
          if (response.status >= 500) {
            throw new ApiError(statusMessage(response.status), { status: response.status });
          }
          return null;
        }
        const session = (await response.json()) as LoginResponse;
        if (!session.access_token) {
          return null;
        }
        setAccessToken(session.access_token);
        return session;
      } catch (error) {
        // The deliberate 5xx throw above must survive; only a fetch that never
        // reached the server (TypeError) reads as "no session to restore".
        if (error instanceof ApiError) {
          throw error;
        }
        return null;
      }
    })().finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
}

/**
 * Single entry point for every backend call. Returns parsed JSON, or undefined
 * for empty responses (204/205), and throws {@link ApiError} on failure.
 */
export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  return performRequest<T>(path, options, true);
}

async function performRequest<T>(
  path: string,
  options: RequestOptions,
  allowRefresh: boolean,
): Promise<T> {
  const { method = 'GET', body, query, signal } = options;
  const url = buildUrl(path, query);

  const headers = new Headers({ Accept: 'application/json' });
  if (body !== undefined) {
    headers.set('Content-Type', 'application/json');
  }
  if (accessToken) {
    headers.set('Authorization', `Bearer ${accessToken}`);
  }

  let response: Response;
  try {
    response = await fetch(url, {
      method,
      headers,
      signal,
      credentials: 'include',
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      throw new ApiError('The request was aborted.', { cause: error });
    }
    throw new ApiError('Network request failed.', { cause: error });
  }

  if (response.status === 401 && allowRefresh && !isAuthPath(path)) {
    const session = await refreshSession();
    if (session) {
      return performRequest<T>(path, options, false);
    }
    setAccessToken(null);
    authExpiredListeners.forEach((listener) => listener());
    throw new ApiError(SESSION_EXPIRED_MESSAGE, { status: response.status });
  }

  const raw = await response.text();
  let parsed: unknown;
  if (raw) {
    try {
      parsed = JSON.parse(raw);
    } catch {
      parsed = undefined;
    }
  }

  if (!response.ok) {
    const messageFromBody =
      parsed && typeof (parsed as { message?: unknown }).message === 'string'
        ? (parsed as { message: string }).message
        : undefined;

    throw new ApiError(messageFromBody ?? statusMessage(response.status), {
      status: response.status,
      details: parsed ?? raw ?? undefined,
    });
  }

  return parsed as T;
}
