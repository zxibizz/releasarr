import { apiRequest } from '@/lib/api/client';
import type {
  Indexer,
  IndexerEventType,
  IndexerHistoryResponse,
  IndexerLogLevel,
  IndexerLogsResponse,
  IndexerTestResult,
  IndexersResponse,
  IndexerTestResults,
} from '@/types';

interface ListHistoryParams {
  page: number;
  perPage: number;
  indexerId?: number;
  eventType?: IndexerEventType;
}

interface ListLogsParams {
  page: number;
  perPage: number;
  minLevel?: IndexerLogLevel;
}

export const indexersApi = {
  list: async (signal?: AbortSignal): Promise<Indexer[]> => {
    const response = await apiRequest<IndexersResponse>('/indexers', { signal });
    return response.indexers;
  },

  logs: ({ page, perPage, minLevel }: ListLogsParams, signal?: AbortSignal) =>
    apiRequest<IndexerLogsResponse>('/indexers/logs', {
      signal,
      query: {
        page,
        per_page: perPage,
        ...(minLevel ? { min_level: minLevel } : {}),
      },
    }),

  history: ({ page, perPage, indexerId, eventType }: ListHistoryParams, signal?: AbortSignal) =>
    apiRequest<IndexerHistoryResponse>('/indexers/history', {
      signal,
      query: {
        page,
        per_page: perPage,
        ...(indexerId === undefined ? {} : { indexer_id: indexerId }),
        ...(eventType ? { event_type: eventType } : {}),
      },
    }),

  test: (indexerId: number) =>
    apiRequest<IndexerTestResult>(`/indexers/${indexerId}/test`, { method: 'POST' }),

  testAll: async (): Promise<IndexerTestResult[]> => {
    const response = await apiRequest<IndexerTestResults>('/indexers/test', { method: 'POST' });
    return response.results;
  },
};
