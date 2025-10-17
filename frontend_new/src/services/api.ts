import { MediaRequest, Release, ReleaseStats, RequestsResponse, TorrentSearchResponse } from '../types';
import {
  getMockRelease,
  getMockReleases,
  getMockReleasesByRequest,
  getMockReleasesByStatus,
  getMockReleaseStats,
  getMockRequest,
  getMockRequests,
  searchMockTorrents,
  updateMockReleaseFileMapping
} from './mockData';

// API configuration
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

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
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  // Requests endpoints
  async getRequests(page: number = 1, perPage: number = 20): Promise<RequestsResponse> {
    // For now, use mock data but structure for real API
    const requests = await getMockRequests();
    return {
      requests,
      total: requests.length,
      page,
      per_page: perPage
    };
  }

  async getRequest(id: string): Promise<MediaRequest> {
    // For now, use mock data but structure for real API
    const request = await getMockRequest(id);
    if (!request) {
      throw new Error('Request not found');
    }
    return request;
  }

  async searchTorrents(query: string): Promise<TorrentSearchResponse> {
    // For now, use mock data but structure for real API
    const results = await searchMockTorrents(query);
    return {
      results,
      query,
      total_results: results.length
    };
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

  async downloadTorrent(torrentLink: string, requestId: string): Promise<void> {
    return this.request<void>('/torrents/download', {
      method: 'POST',
      body: JSON.stringify({ torrent_link: torrentLink, request_id: requestId }),
    });
  }

  // Releases endpoints
  async getReleases(): Promise<Release[]> {
    // For now, use mock data but structure for real API
    return getMockReleases();
  }

  async getRelease(id: string): Promise<Release> {
    // For now, use mock data but structure for real API
    const release = await getMockRelease(id);
    if (!release) {
      throw new Error('Release not found');
    }
    return release;
  }

  async getReleasesByRequest(requestId: string): Promise<Release[]> {
    // For now, use mock data but structure for real API
    return getMockReleasesByRequest(requestId);
  }

  async getReleasesByStatus(status: string): Promise<Release[]> {
    // For now, use mock data but structure for real API
    return getMockReleasesByStatus(status);
  }

  async getReleaseStats(): Promise<ReleaseStats> {
    // For now, use mock data but structure for real API
    return getMockReleaseStats();
  }

  async updateReleaseFileMapping(
    releaseId: string,
    fileId: string,
    mapping: { episode_mapping?: any; request_mapping?: any }
  ): Promise<boolean> {
    // For now, use mock data but structure for real API
    return updateMockReleaseFileMapping(releaseId, fileId, mapping);
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

  async addRelease(torrentData: { magnet_link: string; request_ids: string[] }): Promise<Release> {
    return this.request<Release>('/releases', {
      method: 'POST',
      body: JSON.stringify(torrentData),
    });
  }
}

// Create and export API client instance
export const apiClient = new ApiClient();

// Convenience functions that match the current mock API
export const fetchRequests = () => apiClient.getRequests();
export const fetchRequest = (id: string) => apiClient.getRequest(id);
export const searchTorrents = (query: string) => apiClient.searchTorrents(query);

// Release convenience functions
export const fetchReleases = () => apiClient.getReleases();
export const fetchRelease = (id: string) => apiClient.getRelease(id);
export const fetchReleasesByRequest = (requestId: string) => apiClient.getReleasesByRequest(requestId);
export const fetchReleasesByStatus = (status: string) => apiClient.getReleasesByStatus(status);
export const fetchReleaseStats = () => apiClient.getReleaseStats();
export const updateReleaseFileMapping = (releaseId: string, fileId: string, mapping: any) => 
  apiClient.updateReleaseFileMapping(releaseId, fileId, mapping);

// Export the class for testing or custom instances
export { ApiClient };
