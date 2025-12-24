import { useCallback, useEffect, useState } from 'react';
import { fetchRequest as fetchRequestAPI, fetchRequests as fetchRequestsAPI } from '../services/api';
import { MediaRequest, MovieRequest, RequestsResponse, SeriesRequest } from '../types';

const REQUEST_STATUSES: ReadonlyArray<MediaRequest['status']> = [
  'pending',
  'searching',
  'downloading',
  'completed',
  'failed',
] as const;

const REQUEST_TYPES: ReadonlyArray<MediaRequest['type']> = ['movie', 'series'] as const;

const STATUS_SET = new Set<MediaRequest['status']>(REQUEST_STATUSES);
const TYPE_SET = new Set<MediaRequest['type']>(REQUEST_TYPES);

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null;

const safeString = (value: unknown, fallback = ''): string => {
  if (typeof value === 'string') {
    return value;
  }
  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }
  return fallback;
};

const safeNonEmptyString = (value: unknown, fallback: string): string => {
  const stringValue = safeString(value).trim();
  return stringValue.length > 0 ? stringValue : fallback;
};

const safeNumber = (value: unknown, fallback: number): number => {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === 'string') {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }
  return fallback;
};

const toStringArray = (value: unknown): string[] => {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map((item) => safeString(item).trim())
    .filter((item): item is string => item.length > 0);
};

const toIsoString = (value: unknown): string => {
  const candidate = safeString(value).trim();
  if (candidate) {
    const parsed = Date.parse(candidate);
    if (!Number.isNaN(parsed)) {
      return new Date(parsed).toISOString();
    }
  }
  return new Date().toISOString();
};

const toStatus = (value: unknown): MediaRequest['status'] => {
  if (typeof value === 'string' && STATUS_SET.has(value as MediaRequest['status'])) {
    return value as MediaRequest['status'];
  }
  return 'pending';
};

const toType = (value: unknown): MediaRequest['type'] | null => {
  if (typeof value === 'string' && TYPE_SET.has(value as MediaRequest['type'])) {
    return value as MediaRequest['type'];
  }
  return null;
};

const sanitizeMediaRequest = (raw: unknown): MediaRequest | null => {
  if (!isRecord(raw)) {
    return null;
  }

  const id = safeNonEmptyString(raw.id, '');
  const type = toType(raw.type);
  if (!id || !type) {
    return null;
  }

  const title = safeNonEmptyString(raw.title, `Request ${id}`);
  const year = safeNumber(raw.year, 0);

  const baseRequest = {
    id,
    title,
    year,
    poster_url: safeString(raw.poster_url, ''),
    overview: safeString(raw.overview, ''),
    genres: toStringArray(raw.genres),
    status: toStatus(raw.status),
    created_at: toIsoString(raw.created_at),
    updated_at: toIsoString(raw.updated_at),
  };

  if (type === 'movie') {
    const movieRequest: MovieRequest = {
      ...baseRequest,
      type: 'movie',
      runtime: safeNumber(raw.runtime, 0),
      imdb_id: safeString(raw.imdb_id, ''),
    };
    return movieRequest;
  }

  const seriesRequest: SeriesRequest = {
    ...baseRequest,
    type: 'series',
    season_number: safeNumber(raw.season_number, 1),
    total_episodes: safeNumber(raw.total_episodes, 0),
    series_title: safeNonEmptyString(raw.series_title, title),
    series_year: safeNumber(raw.series_year, year),
    imdb_id: safeString(raw.imdb_id, ''),
  };

  return seriesRequest;
};

const parseRequestsResponse = (payload: unknown) => {
  if (!payload || typeof payload !== 'object') {
    return { requests: null as MediaRequest[] | null, dropped: 0, originalLength: 0 };
  }

  const maybeResponse = payload as Partial<RequestsResponse>;
  if (!Array.isArray(maybeResponse.requests)) {
    return { requests: null as MediaRequest[] | null, dropped: 0, originalLength: 0 };
  }

  const sanitized: MediaRequest[] = [];
  let dropped = 0;
  maybeResponse.requests.forEach((item, index) => {
    const normalized = sanitizeMediaRequest(item);
    if (normalized) {
      sanitized.push(normalized);
    } else {
      dropped += 1;
      console.warn('Discarding malformed request from API response', { index, item });
    }
  });

  return {
    requests: sanitized,
    dropped,
    originalLength: maybeResponse.requests.length,
  };
};

export const useRequests = () => {
  const [requests, setRequests] = useState<MediaRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadRequests = useCallback(async (params?: Parameters<typeof fetchRequestsAPI>[0]) => {
    try {
      setLoading(true);
      setError(null);
      const response: RequestsResponse = await fetchRequestsAPI(params);
      const { requests: sanitized, dropped, originalLength } = parseRequestsResponse(response);

      if (!sanitized) {
        setError('Unexpected response format received from the server.');
        return [];
      }

      if (originalLength > 0 && sanitized.length === 0) {
        setError('No valid request data returned from the server.');
        return [];
      }

      if (dropped > 0) {
        console.warn(
          `Discarded ${dropped} malformed request record${dropped === 1 ? '' : 's'} from API response.`,
        );
      }

      setRequests(sanitized);
      return sanitized;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch requests';
      setError(message);
      return [];
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchRequestsByStatus = async (status: string) => {
    await loadRequests({ status: status as MediaRequest['status'] });
  };

  const fetchRequestsByType = async (type: 'movie' | 'series') => {
    await loadRequests({ type });
  };

  useEffect(() => {
    loadRequests();
  }, [loadRequests]);

  return {
    requests,
    loading,
    error,
    refetch: () => loadRequests(),
    fetchByStatus: fetchRequestsByStatus,
    fetchByType: fetchRequestsByType
  };
};

export const useRequest = (id: string) => {
  const [request, setRequest] = useState<MediaRequest | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchRequest = useCallback(async () => {
    if (!id) {
      setRequest(null);
      setError('Missing request identifier');
      setLoading(false);
      return null;
    }

    try {
      setLoading(true);
      setError(null);
      const data = await fetchRequestAPI(id);
      const sanitized = sanitizeMediaRequest(data);
      if (!sanitized) {
        setRequest(null);
        throw new Error('Received malformed request data from the server.');
      }
      setRequest(sanitized);
      return sanitized;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch request';
      setError(message);
      setRequest(null);
      throw err instanceof Error ? err : new Error(message);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    if (!id) {
      return;
    }

    fetchRequest().catch(() => {
      // Errors are handled via local state; suppress console noise here.
    });
  }, [id, fetchRequest]);

  return {
    request,
    loading,
    error,
    refetch: fetchRequest
  };
};
