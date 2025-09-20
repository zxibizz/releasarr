import { useCallback, useState } from 'react';
import { searchTorrents as searchTorrentsAPI } from '../services/api';
import { SearchState, TorrentResult } from '../types';

export const useTorrentSearch = () => {
  const [searchState, setSearchState] = useState<SearchState>({
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
      const response = await searchTorrentsAPI(query);
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

  const selectTorrent = useCallback((torrent: TorrentResult) => {
    // In a real implementation, this would trigger the download
    console.log('Selected torrent:', torrent);
    // You could add additional logic here like showing a success message
  }, []);

  return {
    searchState,
    search,
    clearSearch,
    selectTorrent
  };
};
