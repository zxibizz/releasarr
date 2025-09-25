import { apiClient } from '@/services/api';
import type {
  MediaRequest,
  RequestsResponse,
  RequestsSummaryResponse,
  RequestLogEntry,
} from '@/types';

import type { RequestListFilters } from './queryKeys';

export const requestsApi = {
  list(filters?: RequestListFilters): Promise<RequestsResponse> {
    return apiClient.getRequests(filters);
  },
  detail(id: string): Promise<MediaRequest> {
    return apiClient.getRequest(id);
  },
  summary(ids: string[]): Promise<RequestsSummaryResponse> {
    return apiClient.getRequestsSummary(ids);
  },
  logs(requestId: string): Promise<RequestLogEntry[]> {
    return apiClient.getRequestLogs({ requestId });
  },
} as const;
