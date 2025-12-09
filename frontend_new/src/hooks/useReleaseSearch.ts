import { useCallback, useState } from 'react';
import {
  downloadReleaseCandidate as downloadReleaseCandidateAPI,
  searchReleaseCandidates as searchReleaseCandidatesAPI,
} from '../services/api';
import {
  DownloadReleaseResponse,
  ReleaseDownloadRequest,
  ReleaseSearchResponse,
  ReleaseSearchResult,
  ReleaseSearchState,
} from '../types';

export const useReleaseSearch = () => {
  const [searchState, setSearchState] = useState<ReleaseSearchState>({
    query: '',
    results: [],
    loading: false,
    error: null
  });

  const search = useCallback(async (query: string, requestId?: string): Promise<ReleaseSearchResponse | null> => {
    const trimmedQuery = query.trim();
    if (!trimmedQuery) {
      setSearchState(prev => ({
        ...prev,
        query: '',
        results: [],
        error: null
      }));
      return null;
    }

    setSearchState(prev => ({
      ...prev,
      query: trimmedQuery,
      loading: true,
      error: null
    }));

    try {
      const response = await searchReleaseCandidatesAPI(trimmedQuery, requestId);
      setSearchState(prev => ({
        ...prev,
        query: response?.query ?? trimmedQuery,
        results: Array.isArray(response?.results) ? response.results : [],
        loading: false
      }));
      return response ?? null;
    } catch (err) {
      const status = typeof err === 'object' && err !== null && 'status' in err
        ? (err as { status?: number }).status
        : undefined;

      if (status === 404) {
        setSearchState(prev => ({
          ...prev,
          query: trimmedQuery,
          results: [],
          loading: false,
          error: null,
        }));
        return null;
      }

      const message = err instanceof Error ? err.message : 'Search failed';
      setSearchState(prev => ({
        ...prev,
        results: [],
        loading: false,
        error: message
      }));
      throw new Error(message);
    }
  }, []);

  const clearSearch = useCallback(() => {
    setSearchState({
      query: '',
      results: [],
      loading: false,
      error: null
    });
  }, []);

  const selectReleaseCandidate = useCallback(
    async (candidate: ReleaseSearchResult, requestId: string): Promise<DownloadReleaseResponse> => {
      const resolvedRequestId = candidate.request_id ?? requestId;
      if (!resolvedRequestId) {
        throw new Error('A request id is required to download a release.');
      }

      const payload: ReleaseDownloadRequest = {
        release_id: candidate.release_id,
      };

      try {
        const response = await downloadReleaseCandidateAPI(
          resolvedRequestId,
          payload,
        );
        return response;
      } catch (error) {
        const message =
          error instanceof Error ? error.message : 'Failed to queue download';
        throw new Error(message);
      }
    },
    [],
  );

  return {
    searchState,
    search,
    clearSearch,
    selectReleaseCandidate
  };
};
