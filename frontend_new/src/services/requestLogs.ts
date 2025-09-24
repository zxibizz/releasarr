import { apiClient } from '@/services/api';
import type { RequestLogEntry } from '@/types';

export const fetchRequestLogs = async (requestId: string): Promise<RequestLogEntry[]> => {
  if (!requestId) {
    return [];
  }

  return apiClient.getRequestLogs({ requestId });
};
