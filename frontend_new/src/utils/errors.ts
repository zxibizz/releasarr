import { ApiError } from '@/services/api';

const STATUS_TITLES: Record<number, string> = {
  400: 'Invalid Request',
  401: 'Authentication Required',
  403: 'Access Denied',
  404: 'Not Found',
  409: 'Request Conflict',
  422: 'Unprocessable Request',
  429: 'Too Many Requests',
  500: 'Server Error',
  502: 'Gateway Error',
  503: 'Service Unavailable',
  504: 'Request Timed Out',
};

export interface ApiErrorInfo {
  title?: string;
  description: string;
  status?: number;
  details?: string;
}

export const isApiError = (error: unknown): error is ApiError => error instanceof ApiError;

const normaliseDetails = (details: unknown): string | undefined => {
  if (!details) {
    return undefined;
  }

  if (typeof details === 'string') {
    return details;
  }

  if (Array.isArray(details)) {
    return details.map((item) => normaliseDetails(item) ?? String(item)).join('\n');
  }

  if (typeof details === 'object') {
    try {
      return JSON.stringify(details, null, 2);
    } catch {
      return undefined;
    }
  }

  return typeof details === 'number' || typeof details === 'boolean'
    ? String(details)
    : undefined;
};

export const getApiErrorInfo = (
  error: unknown,
  fallback: { title?: string; description: string },
): ApiErrorInfo => {
  if (isApiError(error)) {
    const title = error.status && STATUS_TITLES[error.status] ? STATUS_TITLES[error.status] : fallback.title;
    return {
      title,
      description: error.message || fallback.description,
      status: error.status,
      details: normaliseDetails(error.details),
    };
  }

  if (error instanceof Error) {
    return {
      title: fallback.title,
      description: error.message,
    };
  }

  if (typeof error === 'string') {
    return {
      title: fallback.title,
      description: error,
    };
  }

  return fallback;
};

export const formatErrorDebugInfo = (error: unknown): string | undefined => {
  if (!error) {
    return undefined;
  }

  if (isApiError(error)) {
    if (error.details) {
      return normaliseDetails(error.details);
    }
    if (error.body) {
      return error.body;
    }
    return undefined;
  }

  if (error instanceof Error && error.stack) {
    return error.stack;
  }

  if (typeof error === 'object') {
    try {
      return JSON.stringify(error, null, 2);
    } catch {
      return undefined;
    }
  }

  return undefined;
};
