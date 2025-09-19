import { useEffect, useState } from 'react';
import { getMockRequest, getMockRequests, getMockRequestsByStatus, getMockRequestsByType } from '../services/mockData';
import { MediaRequest } from '../types';

export const useRequests = () => {
  const [requests, setRequests] = useState<MediaRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchRequests = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getMockRequests();
      setRequests(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch requests');
    } finally {
      setLoading(false);
    }
  };

  const fetchRequestsByStatus = async (status: string) => {
    try {
      setLoading(true);
      setError(null);
      const data = await getMockRequestsByStatus(status);
      setRequests(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch requests');
    } finally {
      setLoading(false);
    }
  };

  const fetchRequestsByType = async (type: 'movie' | 'series') => {
    try {
      setLoading(true);
      setError(null);
      const data = await getMockRequestsByType(type);
      setRequests(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch requests');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRequests();
  }, []);

  return {
    requests,
    loading,
    error,
    refetch: fetchRequests,
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
      const data = await getMockRequest(id);
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
