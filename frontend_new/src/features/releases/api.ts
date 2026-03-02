import { apiClient } from '@/services/api';
import type {
  AsyncOperationResponse,
  Release,
  ReleaseDownloadRequest,
  ReleaseFileMappingInput,
  ReleaseSearchResponse,
} from '@/types';

import type { ReleaseListFilters } from './queryKeys';

export const releasesApi = {
  list(filters?: ReleaseListFilters): Promise<Release[]> {
    return apiClient.getReleases(filters);
  },
  detail(id: string): Promise<Release> {
    return apiClient.getRelease(id);
  },
  byRequest(requestId: string): Promise<Release[]> {
    return apiClient.getReleasesByRequest(requestId);
  },
  byStatus(status: Release['status']): Promise<Release[]> {
    return apiClient.getReleasesByStatus(status);
  },
  updateFileMappings(releaseId: string, mappings: ReleaseFileMappingInput[]): Promise<boolean> {
    return apiClient.updateReleaseFileMappings(releaseId, mappings);
  },
  pause(id: string): Promise<AsyncOperationResponse> {
    return apiClient.pauseRelease(id);
  },
  resume(id: string): Promise<AsyncOperationResponse> {
    return apiClient.resumeRelease(id);
  },
  delete(id: string): Promise<void> {
    return apiClient.deleteRelease(id);
  },
  add(releaseData: { magnet_link: string; request_ids: string[] }): Promise<Release> {
    return apiClient.addRelease(releaseData);
  },
  searchCandidates(query: string, requestId?: string): Promise<ReleaseSearchResponse | null> {
    return apiClient.searchReleaseCandidates(query, requestId);
  },
  downloadCandidate(requestId: string, payload: ReleaseDownloadRequest): Promise<AsyncOperationResponse> {
    return apiClient.downloadReleaseCandidate(requestId, payload);
  },
} as const;
