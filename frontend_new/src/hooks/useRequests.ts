import { useEffect, useState } from 'react';
import { fetchRequest as fetchRequestAPI, fetchRequests as fetchRequestsAPI } from '../services/api';
import { MediaRequest, RequestsResponse } from '../types';

export const useRequests = () => {
  const [requests, setRequests] = useState<MediaRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadRequests = async (params?: Parameters<typeof fetchRequestsAPI>[0]) => {
    try {
      setLoading(true);
      setError(null);
      const response: RequestsResponse = await fetchRequestsAPI(params);
      setRequests(response.requests);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch requests');
    } finally {
      setLoading(false);
    }
  };

  const fetchRequestsByStatus = async (status: string) => {
    await loadRequests({ status: status as MediaRequest['status'] });
  };

  const fetchRequestsByType = async (type: 'movie' | 'series') => {
    await loadRequests({ type });
  };

  useEffect(() => {
    loadRequests();
  }, []);

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

  const fetchRequest = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchRequestAPI(id);
      setRequest(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch request');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (id) {
      fetchRequest();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  return {
    request,
    loading,
    error,
    refetch: fetchRequest
  };
};
