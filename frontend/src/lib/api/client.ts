const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001/api';
const API_KEY = import.meta.env.VITE_API_KEY ?? 'dev-secret';

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

  constructor(message: string, options: { status?: number; details?: unknown; cause?: unknown } = {}) {
    super(message, { cause: options.cause });
    this.name = 'ApiError';
    this.status = options.status;
    this.details = options.details;
  }
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

/**
 * Single entry point for every backend call. Returns parsed JSON, or undefined
 * for empty responses (204/205), and throws {@link ApiError} on failure.
 */
export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, query, signal } = options;
  const url = buildUrl(path, query);

  const headers = new Headers({ Accept: 'application/json' });
  if (body !== undefined) {
    headers.set('Content-Type', 'application/json');
  }
  if (API_KEY) {
    headers.set('X-API-Key', API_KEY);
  }

  let response: Response;
  try {
    response = await fetch(url, {
      method,
      headers,
      signal,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      throw new ApiError('The request was aborted.', { cause: error });
    }
    throw new ApiError('Network request failed.', { cause: error });
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
