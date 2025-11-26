import {
  DownloadReleaseResponse,
  MediaRequest,
  Release,
  ReleaseDownloadRequest,
  ReleaseFileMappingInput,
  ReleaseSearchResponse,
  RequestsResponse,
} from '../types';
import { RequestLogEntry } from '../types/logs';

// API configuration
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8001/api';

// API client class for future backend integration
class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;

    const config: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      ...options,
    };

    try {
      const response = await fetch(url, config);
      const text = await response.text();

      if (!response.ok) {
        const errorMessage = (() => {
          if (!text) {
            return `Request failed with status ${response.status}`;
          }
          try {
            const parsed = JSON.parse(text);
            if (parsed && typeof parsed.message === 'string') {
              return parsed.message;
            }
          } catch (error) {
            // ignore JSON parse errors
          }
          return `Request failed with status ${response.status}`;
        })();

        const error = new Error(errorMessage) as Error & {
          status?: number;
          body?: string;
          details?: unknown;
        };
        error.status = response.status;
        if (text) {
          error.body = text;
          try {
            error.details = JSON.parse(text);
          } catch (parseError) {
            // body is not JSON, keep raw text only
          }
        }

        throw error;
      }

      if (response.status === 204 || response.status === 205 || !text) {
        return undefined as T;
      }

      return JSON.parse(text) as T;
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  // Requests endpoints
  async getRequests(options: {
    page?: number;
    perPage?: number;
    status?: MediaRequest['status'];
    type?: MediaRequest['type'];
  } = {}): Promise<RequestsResponse> {
    const searchParams = new URLSearchParams();
    if (options.page) searchParams.set('page', String(options.page));
    if (options.perPage) searchParams.set('per_page', String(options.perPage));
    if (options.status) searchParams.set('status', options.status);
    if (options.type) searchParams.set('type', options.type);

    const query = searchParams.toString();
    return this.request<RequestsResponse>(`/requests${query ? `?${query}` : ''}`);
  }

  async getRequest(id: string): Promise<MediaRequest> {
    return this.request<MediaRequest>(`/requests/${id}`);
  }

  async searchReleaseCandidates(
    query: string,
    requestId?: string,
  ): Promise<ReleaseSearchResponse> {
    const searchParams = new URLSearchParams();
    searchParams.set('q', query);
    if (requestId) {
      searchParams.set('request_id', requestId);
    }
    const endpoint = `/releases/search?${searchParams.toString()}`;
    return this.request<ReleaseSearchResponse>(endpoint);
  }

  // Future endpoints for real backend integration
  async createRequest(requestData: Partial<MediaRequest>): Promise<MediaRequest> {
    return this.request<MediaRequest>('/requests', {
      method: 'POST',
      body: JSON.stringify(requestData),
    });
  }

  async updateRequest(id: string, requestData: Partial<MediaRequest>): Promise<MediaRequest> {
    return this.request<MediaRequest>(`/requests/${id}`, {
      method: 'PUT',
      body: JSON.stringify(requestData),
    });
  }

  async deleteRequest(id: string): Promise<void> {
    return this.request<void>(`/requests/${id}`, {
      method: 'DELETE',
    });
  }

  async downloadReleaseCandidate(
    requestId: string,
    payload: ReleaseDownloadRequest,
  ): Promise<DownloadReleaseResponse> {
    return this.request<DownloadReleaseResponse>(
      `/requests/${requestId}/releases/download`,
      {
        method: 'POST',
        body: JSON.stringify(payload),
      }
    );
  }

  // Releases endpoints
  async getReleases(filters: { status?: Release['status']; requestId?: string } = {}): Promise<Release[]> {
    const searchParams = new URLSearchParams();
    if (filters.status) searchParams.set('status', filters.status);
    if (filters.requestId) searchParams.set('request_id', filters.requestId);
    const query = searchParams.toString();
    return this.request<Release[]>(`/releases${query ? `?${query}` : ''}`);
  }

  async getRelease(id: string): Promise<Release> {
    return this.request<Release>(`/releases/${id}`);
  }

  async getReleasesByRequest(requestId: string): Promise<Release[]> {
    return this.request<Release[]>(`/requests/${requestId}/releases`);
  }

  async getReleasesByStatus(status: string): Promise<Release[]> {
    return this.getReleases({ status: status as Release['status'] });
  }

  async getRequestLogs(params: { requestId?: string } = {}): Promise<RequestLogEntry[]> {
    const searchParams = new URLSearchParams();
    if (params.requestId) {
      searchParams.set('request_id', params.requestId);
    }
    const query = searchParams.toString();
    return this.request<RequestLogEntry[]>(`/logs${query ? `?${query}` : ''}`);
  }

  async updateReleaseFileMappings(
    releaseId: string,
    mappings: ReleaseFileMappingInput[],
  ): Promise<boolean> {
    const response = await this.request<{ success: boolean }>(
      `/releases/${releaseId}/files/mapping`,
      {
        method: 'PUT',
        body: JSON.stringify({ files: mappings }),
      }
    );
    return response?.success ?? false;
  }

  // Future release endpoints for real backend integration
  async pauseRelease(id: string): Promise<void> {
    return this.request<void>(`/releases/${id}/pause`, {
      method: 'POST',
    });
  }

  async resumeRelease(id: string): Promise<void> {
    return this.request<void>(`/releases/${id}/resume`, {
      method: 'POST',
    });
  }

  async deleteRelease(id: string): Promise<void> {
    return this.request<void>(`/releases/${id}`, {
      method: 'DELETE',
    });
  }

  async addRelease(releaseData: { magnet_link: string; request_ids: string[] }): Promise<Release> {
    return this.request<Release>('/releases', {
      method: 'POST',
      body: JSON.stringify(releaseData),
    });
  }
}

// Create and export API client instance
export const apiClient = new ApiClient();

// Convenience functions that match the current mock API
export const fetchRequests = (options?: {
  page?: number;
  perPage?: number;
  status?: MediaRequest['status'];
  type?: MediaRequest['type'];
}) => apiClient.getRequests(options);
export const fetchRequest = (id: string) => apiClient.getRequest(id);
// Release convenience functions
export const fetchReleases = (filters?: { status?: Release['status']; requestId?: string }) =>
  apiClient.getReleases(filters);
export const fetchRelease = (id: string) => apiClient.getRelease(id);
export const fetchReleasesByRequest = (requestId: string) => apiClient.getReleasesByRequest(requestId);
export const fetchReleasesByStatus = (status: string) => apiClient.getReleasesByStatus(status);
export const updateReleaseFileMappings = (releaseId: string, mappings: ReleaseFileMappingInput[]) =>
  apiClient.updateReleaseFileMappings(releaseId, mappings);
export const deleteRelease = (id: string) => apiClient.deleteRelease(id);
export const searchReleaseCandidates = (query: string, requestId?: string) =>
  apiClient.searchReleaseCandidates(query, requestId);
export const downloadReleaseCandidate = (
  requestId: string,
  payload: ReleaseDownloadRequest,
) => apiClient.downloadReleaseCandidate(requestId, payload);
export const fetchRequestLogsApi = (requestId?: string) =>
  apiClient.getRequestLogs({ requestId });

// Export the class for testing or custom instances
export { ApiClient };
