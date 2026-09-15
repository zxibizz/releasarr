import { apiRequest } from '@/lib/api/client';
import type {
  AsyncOperationResponse,
  ManualReleaseRequest,
  Release,
  ReleaseDownloadRequest,
  ReleaseFileMappingInput,
  ReleaseFileMappingSuggestion,
  ReleaseFileMappingSuggestions,
  ReleaseRefreshResponse,
  ReleaseSearchResponse,
  ReleasesResponse,
  SuccessResponse,
} from '@/types';

const encode = encodeURIComponent;

export const releasesApi = {
  byRequest: async (requestId: string, signal?: AbortSignal): Promise<Release[]> => {
    const response = await apiRequest<ReleasesResponse>(`/requests/${encode(requestId)}/releases`, {
      signal,
    });
    return response.releases;
  },

  /** Ask the server to re-check this request's releases and return them as they now stand. */
  refreshRequest: (requestId: string) =>
    apiRequest<ReleaseRefreshResponse>(`/requests/${encode(requestId)}/releases/refresh`, {
      method: 'POST',
    }),

  search: (query: string, requestId?: string, signal?: AbortSignal) =>
    apiRequest<ReleaseSearchResponse>('/releases/search', {
      signal,
      query: { q: query, request_id: requestId },
    }),

  queueDownload: (requestId: string, payload: ReleaseDownloadRequest) =>
    apiRequest<AsyncOperationResponse>(`/requests/${encode(requestId)}/releases/download`, {
      method: 'POST',
      body: payload,
    }),

  queueManual: (requestId: string, payload: ManualReleaseRequest) =>
    apiRequest<AsyncOperationResponse>(`/requests/${encode(requestId)}/releases/manual`, {
      method: 'POST',
      body: payload,
    }),

  pause: (releaseId: string) =>
    apiRequest<AsyncOperationResponse>(`/releases/${encode(releaseId)}/pause`, { method: 'POST' }),

  resume: (releaseId: string) =>
    apiRequest<AsyncOperationResponse>(`/releases/${encode(releaseId)}/resume`, { method: 'POST' }),

  remove: (releaseId: string) =>
    apiRequest<void>(`/releases/${encode(releaseId)}`, { method: 'DELETE' }),

  updateFileMappings: async (
    releaseId: string,
    files: ReleaseFileMappingInput[],
  ): Promise<boolean> => {
    const response = await apiRequest<SuccessResponse>(
      `/releases/${encode(releaseId)}/files/mapping`,
      { method: 'PUT', body: { files } },
    );
    return response.success;
  },

  suggestedFileMappings: async (
    releaseId: string,
    signal?: AbortSignal,
  ): Promise<ReleaseFileMappingSuggestion[]> => {
    const response = await apiRequest<ReleaseFileMappingSuggestions>(
      `/releases/${encode(releaseId)}/files/mapping/suggestions`,
      { signal },
    );
    return response.files;
  },
};
