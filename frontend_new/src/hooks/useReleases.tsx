import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import {
  fetchRelease,
  fetchReleases,
  fetchReleasesByRequest,
  fetchReleasesByStatus,
  updateReleaseFileMappings as updateFileMappingsAPI,
} from '../services/api';
import { Release, ReleaseFileMappingInput } from '../types';

interface ReleaseCollectionState {
  releases: Release[];
  loading: boolean;
  error: string | null;
}

interface ReleasesContextValue {
  getCollectionState: (key: string) => ReleaseCollectionState;
  fetchAllReleases: (options?: { force?: boolean }) => Promise<Release[]>;
  fetchByRequest: (
    requestId: string,
    options?: { force?: boolean },
  ) => Promise<Release[]>;
  fetchByStatus: (
    status: string,
    options?: { force?: boolean },
  ) => Promise<Release[]>;
  getReleaseFromCache: (id: string) => Release | null;
  fetchReleaseById: (
    id: string,
    options?: { force?: boolean },
  ) => Promise<Release | null>;
  updateReleaseInCache: (release: Release) => void;
  removeReleaseFromCache: (id: string) => void;
}

const DEFAULT_COLLECTION_STATE: ReleaseCollectionState = {
  releases: [],
  loading: false,
  error: null,
};

const collectionKey = {
  all: 'all',
  request: (requestId: string) => `request:${requestId}`,
  status: (status: string) => `status:${status}`,
};

const ReleasesContext = createContext<ReleasesContextValue | undefined>(undefined);

export const ReleasesProvider = ({ children }: { children: ReactNode }) => {
  const [collections, setCollections] = useState<Record<string, ReleaseCollectionState>>({});
  const [releaseCache, setReleaseCache] = useState<Record<string, Release>>({});
  const collectionsRef = useRef(collections);

  useEffect(() => {
    collectionsRef.current = collections;
  }, [collections]);

  const mergeReleaseCache = useCallback((items: Release[]) => {
    if (items.length === 0) {
      return;
    }

    setReleaseCache((prev) => {
      let changed = false;
      const next = { ...prev };
      items.forEach((item) => {
        const existing = next[item.id];
        if (!existing || existing !== item) {
          next[item.id] = item;
          changed = true;
        }
      });
      return changed ? next : prev;
    });
  }, []);

  const updateReleaseReferences = useCallback((release: Release) => {
    setCollections((prev) => {
      let mutated = false;
      const entries = Object.entries(prev).map(([key, state]) => {
        const index = state.releases.findIndex((item) => item.id === release.id);
        if (index === -1) {
          return [key, state] as const;
        }
        const updatedReleases = [...state.releases];
        updatedReleases[index] = release;
        mutated = true;
        return [key, { ...state, releases: updatedReleases }] as const;
      });

      if (!mutated) {
        return prev;
      }

      return Object.fromEntries(entries);
    });
  }, []);

  const removeReleaseReferences = useCallback((releaseId: string) => {
    setCollections((prev) => {
      let mutated = false;
      const entries = Object.entries(prev).map(([key, state]) => {
        const filtered = state.releases.filter((release) => release.id !== releaseId);
        if (filtered.length === state.releases.length) {
          return [key, state] as const;
        }
        mutated = true;
        return [key, { ...state, releases: filtered }] as const;
      });

      if (!mutated) {
        return prev;
      }

      return Object.fromEntries(entries);
    });

    setReleaseCache((prev) => {
      if (!(releaseId in prev)) {
        return prev;
      }
      const next = { ...prev };
      delete next[releaseId];
      return next;
    });
  }, []);

  const setCollectionState = useCallback(
    (key: string, updater: (current: ReleaseCollectionState) => ReleaseCollectionState) => {
      setCollections((prev) => {
        const current = prev[key] ?? DEFAULT_COLLECTION_STATE;
        const nextState = updater(current);
        if (
          current.releases === nextState.releases &&
          current.loading === nextState.loading &&
          current.error === nextState.error
        ) {
          return prev;
        }
        return { ...prev, [key]: nextState };
      });
    },
    [],
  );

  const fetchCollection = useCallback(
    async (
      key: string,
      loader: () => Promise<Release[]>,
      options?: { force?: boolean },
    ) => {
      const force = options?.force ?? false;
      const existing = collectionsRef.current[key];

      if (!force && existing && existing.releases.length > 0 && !existing.error) {
        return existing.releases;
      }

      setCollectionState(key, (current) => ({ ...current, loading: true, error: null }));

      try {
        const releases = await loader();
        mergeReleaseCache(releases);
        setCollectionState(key, () => ({ releases, loading: false, error: null }));
        return releases;
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to load releases';
        setCollectionState(key, (current) => ({ ...current, loading: false, error: message }));
        return [];
      }
    },
    [mergeReleaseCache, setCollectionState],
  );

  const fetchAllReleases = useCallback(
    async (options?: { force?: boolean }) => {
      return fetchCollection(collectionKey.all, fetchReleases, options);
    },
    [fetchCollection],
  );

  const fetchByRequest = useCallback(
    async (requestId: string, options?: { force?: boolean }) => {
      if (!requestId) {
        return [];
      }
      return fetchCollection(collectionKey.request(requestId), () => fetchReleasesByRequest(requestId), options);
    },
    [fetchCollection],
  );

  const fetchByStatus = useCallback(
    async (status: string, options?: { force?: boolean }) => {
      if (!status) {
        return [];
      }
      return fetchCollection(collectionKey.status(status), () => fetchReleasesByStatus(status), options);
    },
    [fetchCollection],
  );

  const getCollectionState = useCallback(
    (key: string): ReleaseCollectionState => collections[key] ?? DEFAULT_COLLECTION_STATE,
    [collections],
  );

  const getReleaseFromCache = useCallback(
    (id: string) => releaseCache[id] ?? null,
    [releaseCache],
  );

  const updateReleaseInCache = useCallback(
    (release: Release) => {
      mergeReleaseCache([release]);
      updateReleaseReferences(release);
    },
    [mergeReleaseCache, updateReleaseReferences],
  );

  const fetchReleaseById = useCallback(
    async (id: string, options?: { force?: boolean }) => {
      if (!id) {
        throw new Error('Missing release identifier');
      }

      const force = options?.force ?? false;
      const cached = releaseCache[id];
      if (cached && !force) {
        return cached;
      }

      try {
        const release = await fetchRelease(id);
        updateReleaseInCache(release);
        return release;
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to fetch release';
        throw new Error(message);
      }
    },
    [releaseCache, updateReleaseInCache],
  );

  const removeReleaseFromCache = useCallback(
    (id: string) => {
      removeReleaseReferences(id);
    },
    [removeReleaseReferences],
  );

  useEffect(() => {
    fetchAllReleases();
  }, [fetchAllReleases]);

  const value = useMemo<ReleasesContextValue>(
    () => ({
      getCollectionState,
      fetchAllReleases,
      fetchByRequest,
      fetchByStatus,
      getReleaseFromCache,
      fetchReleaseById,
      updateReleaseInCache,
      removeReleaseFromCache,
    }),
    [
      getCollectionState,
      fetchAllReleases,
      fetchByRequest,
      fetchByStatus,
      getReleaseFromCache,
      fetchReleaseById,
      updateReleaseInCache,
      removeReleaseFromCache,
    ],
  );

  return <ReleasesContext.Provider value={value}>{children}</ReleasesContext.Provider>;
};

const useReleasesContext = () => {
  const context = useContext(ReleasesContext);
  if (!context) {
    throw new Error('useReleases must be used within a ReleasesProvider');
  }
  return context;
};

export const useReleases = () => {
  const { getCollectionState, fetchAllReleases } = useReleasesContext();
  const { releases, loading, error } = getCollectionState(collectionKey.all);

  useEffect(() => {
    if (!loading && !error && releases.length === 0) {
      fetchAllReleases();
    }
  }, [fetchAllReleases, loading, error, releases.length]);

  return {
    releases,
    loading,
    error,
    refetch: () => fetchAllReleases({ force: true }),
  };
};

export const useRelease = (id: string) => {
  const { getReleaseFromCache, fetchReleaseById } = useReleasesContext();
  const cachedRelease = id ? getReleaseFromCache(id) : null;
  const [loading, setLoading] = useState<boolean>(!cachedRelease && Boolean(id));
  const [error, setError] = useState<string | null>(null);

  const fetchReleaseDetails = useCallback(
    async (options?: { force?: boolean }) => {
      if (!id) {
        const message = 'Missing release identifier';
        setError(message);
        setLoading(false);
        return null;
      }

      setLoading(true);
      setError(null);
      try {
        const result = await fetchReleaseById(id, options);
        setLoading(false);
        setError(null);
        return result;
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to fetch release';
        setError(message);
        setLoading(false);
        throw new Error(message);
      }
    },
    [id, fetchReleaseById],
  );

  useEffect(() => {
    if (!id) {
      setError('Missing release identifier');
      setLoading(false);
      return;
    }

    if (cachedRelease) {
      setLoading(false);
      setError(null);
      return;
    }

    fetchReleaseDetails().catch(() => {
      /* errors handled via state */
    });
  }, [cachedRelease, fetchReleaseDetails, id]);

  return {
    release: cachedRelease,
    loading,
    error,
    refetch: () => fetchReleaseDetails({ force: true }),
  };
};

export const useReleasesByRequest = (requestId: string, refreshToken?: number) => {
  const { getCollectionState, fetchByRequest } = useReleasesContext();
  const { releases, loading, error } = getCollectionState(collectionKey.request(requestId));

  useEffect(() => {
    if (!requestId) {
      return;
    }
    fetchByRequest(requestId, { force: Boolean(refreshToken) });
    // refreshToken is intentionally used as part of the effect dependencies to trigger reloads
    // when the parent toggles it.
  }, [fetchByRequest, requestId, refreshToken]);

  return {
    releases,
    loading,
    error,
    refetch: () => fetchByRequest(requestId, { force: true }),
  };
};

export const useReleasesByStatus = (status: string) => {
  const { getCollectionState, fetchByStatus } = useReleasesContext();
  const { releases, loading, error } = getCollectionState(collectionKey.status(status));

  useEffect(() => {
    if (!status) {
      return;
    }
    fetchByStatus(status);
  }, [fetchByStatus, status]);

  return {
    releases,
    loading,
    error,
    refetch: () => fetchByStatus(status, { force: true }),
  };
};

export const useReleaseFileMapping = () => {
  const { fetchReleaseById } = useReleasesContext();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const updateFileMappings = useCallback(
    async (releaseId: string, mappings: ReleaseFileMappingInput[]) => {
      setLoading(true);
      setError(null);
      try {
        const success = await updateFileMappingsAPI(releaseId, mappings);
        await fetchReleaseById(releaseId, { force: true });
        setLoading(false);
        return success;
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : 'Failed to update file mapping';
        setError(errorMessage);
        setLoading(false);
        throw new Error(errorMessage);
      }
    },
    [fetchReleaseById],
  );

  return {
    updateFileMappings,
    loading,
    error,
  };
};

export const useReleaseActions = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const performAction = useCallback(async (action: () => Promise<unknown>) => {
    setLoading(true);
    setError(null);
    try {
      const result = await action();
      setLoading(false);
      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Action failed';
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
