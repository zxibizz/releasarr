import { useCallback, useState } from 'react';
import {
  downloadReleaseCandidate as downloadReleaseCandidateAPI,
  searchReleaseCandidates as searchReleaseCandidatesAPI,
} from '../services/api';
import {
  DownloadReleaseResponse,
  ReleaseDownloadRequest,
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

  const search = useCallback(async (query: string, requestId?: string) => {
    if (!query.trim()) {
      setSearchState(prev => ({
        ...prev,
        query: '',
        results: [],
        error: null
      }));
      return;
    }

    setSearchState(prev => ({
      ...prev,
      query,
      loading: true,
      error: null
    }));

    try {
      const response = await searchReleaseCandidatesAPI(query, requestId);
      setSearchState(prev => ({
        ...prev,
        query: response?.query ?? query,
        results: Array.isArray(response?.results) ? response.results : [],
        loading: false
      }));
    } catch (err) {
      const status = typeof err === 'object' && err !== null && 'status' in err
        ? (err as { status?: number }).status
        : undefined;

      if (status === 404) {
        setSearchState(prev => ({
          ...prev,
          query,
          results: [],
          loading: false,
          error: null,
        }));
        return;
      }

      setSearchState(prev => ({
        ...prev,
        results: [],
        loading: false,
        error: err instanceof Error ? err.message : 'Search failed'
      }));
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

      if (!candidate.magnet_link && !candidate.torrent_file_url) {
        throw new Error('This release does not provide a magnet link or torrent URL.');
      }

      const payload: ReleaseDownloadRequest = {
        release_id: candidate.release_id,
        release_name: candidate.release_name,
        request_id: resolvedRequestId,
        magnet_link: candidate.magnet_link,
        torrent_file_url: candidate.torrent_file_url,
        info_url: candidate.info_url,
        quality: candidate.quality,
        source: candidate.source,
        size: candidate.size,
      };

      try {
        const response = await downloadReleaseCandidateAPI(payload);
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
