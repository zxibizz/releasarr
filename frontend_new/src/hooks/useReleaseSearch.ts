import { useCallback, useState } from 'react';
import { searchReleaseCandidates as searchReleaseCandidatesAPI } from '../services/api';
import { ReleaseSearchResult, ReleaseSearchState } from '../types';

export const useReleaseSearch = () => {
  const [searchState, setSearchState] = useState<ReleaseSearchState>({
    query: '',
    results: [],
    loading: false,
    error: null
  });

  const search = useCallback(async (query: string) => {
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
      const response = await searchReleaseCandidatesAPI(query);
      setSearchState(prev => ({
        ...prev,
        results: response.results,
        loading: false
      }));
    } catch (err) {
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

  const selectReleaseCandidate = useCallback((candidate: ReleaseSearchResult) => {
    // In a real implementation, this would trigger the download
    console.log('Selected release candidate:', candidate);
    // You could add additional logic here like showing a success message
  }, []);

  return {
    searchState,
    search,
    clearSearch,
    selectReleaseCandidate
  };
};
