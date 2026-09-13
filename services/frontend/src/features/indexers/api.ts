import { apiRequest } from '@/lib/api/client';
import type {
  Indexer,
  IndexerTestResult,
  IndexersResponse,
  IndexerTestResults,
} from '@/types';

export const indexersApi = {
  list: async (signal?: AbortSignal): Promise<Indexer[]> => {
    const response = await apiRequest<IndexersResponse>('/indexers', { signal });
    return response.indexers;
  },

  test: (indexerId: number) =>
    apiRequest<IndexerTestResult>(`/indexers/${indexerId}/test`, { method: 'POST' }),

  testAll: async (): Promise<IndexerTestResult[]> => {
    const response = await apiRequest<IndexerTestResults>('/indexers/test', { method: 'POST' });
    return response.results;
  },
};
