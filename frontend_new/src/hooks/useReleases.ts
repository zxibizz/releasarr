import { useCallback, useEffect, useState } from 'react';
import {
    fetchRelease,
    fetchReleases,
    fetchReleasesByRequest,
    fetchReleasesByStatus,
    fetchReleaseStats,
    updateReleaseFileMappings as updateFileMappingsAPI
} from '../services/api';
import { Release, ReleaseFileMappingInput, ReleaseStats } from '../types';

export interface UseReleasesState {
  releases: Release[];
  loading: boolean;
  error: string | null;
}

export interface UseReleaseState {
  release: Release | null;
  loading: boolean;
  error: string | null;
}

export interface UseReleaseStatsState {
  stats: ReleaseStats | null;
  loading: boolean;
  error: string | null;
}

export const useReleases = () => {
  const [state, setState] = useState<UseReleasesState>({
    releases: [],
    loading: true,
    error: null,
  });

  const loadReleases = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    try {
      const releases = await fetchReleases();
      setState({ releases, loading: false, error: null });
    } catch (error) {
      setState(prev => ({
        ...prev,
        loading: false,
        error: error instanceof Error ? error.message : 'Failed to load releases',
      }));
    }
  }, []);

  useEffect(() => {
    loadReleases();
  }, [loadReleases]);

  const refetch = useCallback(() => {
    loadReleases();
  }, [loadReleases]);

  return {
    ...state,
    refetch,
  };
};

export const useRelease = (id: string) => {
  const [state, setState] = useState<UseReleaseState>({
    release: null,
    loading: true,
    error: null,
  });

  const loadRelease = useCallback(async (releaseId: string) => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    try {
      const release = await fetchRelease(releaseId);
      setState({ release, loading: false, error: null });
    } catch (error) {
      setState(prev => ({
        ...prev,
        loading: false,
        error: error instanceof Error ? error.message : 'Failed to load release',
      }));
    }
  }, []);

  useEffect(() => {
    if (id) {
      loadRelease(id);
    }
  }, [id, loadRelease]);

  const refetch = useCallback(() => {
    if (id) {
      loadRelease(id);
    }
  }, [id, loadRelease]);

  return {
    ...state,
    refetch,
  };
};

export const useReleasesByRequest = (requestId: string) => {
  const [state, setState] = useState<UseReleasesState>({
    releases: [],
    loading: true,
    error: null,
  });

  const loadReleasesByRequest = useCallback(async (reqId: string) => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    try {
      const releases = await fetchReleasesByRequest(reqId);
      setState({ releases, loading: false, error: null });
    } catch (error) {
      setState(prev => ({
        ...prev,
        loading: false,
        error: error instanceof Error ? error.message : 'Failed to load releases for request',
      }));
    }
  }, []);

  useEffect(() => {
    if (requestId) {
      loadReleasesByRequest(requestId);
    }
  }, [requestId, loadReleasesByRequest]);

  const refetch = useCallback(() => {
    if (requestId) {
      loadReleasesByRequest(requestId);
    }
  }, [requestId, loadReleasesByRequest]);

  return {
    ...state,
    refetch,
  };
};

export const useReleasesByStatus = (status: string) => {
  const [state, setState] = useState<UseReleasesState>({
    releases: [],
    loading: true,
    error: null,
  });

  const loadReleasesByStatus = useCallback(async (releaseStatus: string) => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    try {
      const releases = await fetchReleasesByStatus(releaseStatus);
      setState({ releases, loading: false, error: null });
    } catch (error) {
      setState(prev => ({
        ...prev,
        loading: false,
        error: error instanceof Error ? error.message : 'Failed to load releases by status',
      }));
    }
  }, []);

  useEffect(() => {
    if (status) {
      loadReleasesByStatus(status);
    }
  }, [status, loadReleasesByStatus]);

  const refetch = useCallback(() => {
    if (status) {
      loadReleasesByStatus(status);
    }
  }, [status, loadReleasesByStatus]);

  return {
    ...state,
    refetch,
  };
};

export const useReleaseStats = () => {
  const [state, setState] = useState<UseReleaseStatsState>({
    stats: null,
    loading: true,
    error: null,
  });

  const loadReleaseStats = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    try {
      const stats = await fetchReleaseStats();
      setState({ stats, loading: false, error: null });
    } catch (error) {
      setState(prev => ({
        ...prev,
        loading: false,
        error: error instanceof Error ? error.message : 'Failed to load release stats',
      }));
    }
  }, []);

  useEffect(() => {
    loadReleaseStats();
  }, [loadReleaseStats]);

  const refetch = useCallback(() => {
    loadReleaseStats();
  }, [loadReleaseStats]);

  return {
    ...state,
    refetch,
  };
};

export const useReleaseFileMapping = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const updateFileMappings = useCallback(async (
    releaseId: string,
    mappings: ReleaseFileMappingInput[],
  ) => {
    setLoading(true);
    setError(null);
    try {
      const success = await updateFileMappingsAPI(releaseId, mappings);
      setLoading(false);
      return success;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to update file mapping';
      setError(errorMessage);
      setLoading(false);
      throw new Error(errorMessage);
    }
  }, []);

  return {
    updateFileMappings,
    loading,
    error,
  };
};

export const useReleaseActions = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const performAction = useCallback(async (action: () => Promise<any>) => {
    setLoading(true);
    setError(null);
    try {
      const result = await action();
      setLoading(false);
      return result;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Action failed';
      setError(errorMessage);
      setLoading(false);
      throw new Error(errorMessage);
    }
  }, []);

  return {
    performAction,
    loading,
    error,
  };
};
