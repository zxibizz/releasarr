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

type ApiResponseType = 'json' | 'text' | 'auto';

interface ApiRequestOptions extends RequestInit {
  responseType?: ApiResponseType;
  timeoutMs?: number;
}

interface ApiErrorParams {
  message: string;
  status?: number;
  body?: string;
  details?: unknown;
  url?: string;
  isAbortError?: boolean;
  cause?: unknown;
}

export class ApiError extends Error {
  status?: number;
  body?: string;
  details?: unknown;
  url?: string;
  isAbortError: boolean;

  constructor({ message, status, body, details, url, isAbortError = false, cause }: ApiErrorParams) {
    super(message, { cause });
    this.name = 'ApiError';
    this.status = status;
    this.body = body;
    this.details = details;
    this.url = url;
    this.isAbortError = isAbortError;
  }
}

const HTTP_STATUS_MESSAGES: Record<number, string> = {
  400: 'The request was invalid. Please check the data and try again.',
  401: 'Authentication is required to complete this action.',
  403: 'You do not have permission to complete this action.',
  404: 'The requested resource could not be found.',
  409: 'A conflict prevented this action from completing.',
  422: 'The server could not process the provided data.',
  429: 'Too many requests — please wait before trying again.',
  500: 'The server encountered an error. Please try again later.',
  502: 'Bad gateway — the upstream service returned an invalid response.',
  503: 'The service is temporarily unavailable. Please try again soon.',
  504: 'The service timed out while processing the request.',
};

const getStatusMessage = (status: number): string => {
  if (HTTP_STATUS_MESSAGES[status]) {
    return HTTP_STATUS_MESSAGES[status];
  }
  const statusFamily = Math.floor(status / 100);
  if (statusFamily === 4) {
    return 'The server could not process the request. Please verify the input and retry.';
  }
  if (statusFamily === 5) {
    return 'A server error occurred. Please try again later.';
  }
  return `Request failed with status ${status}`;
};

const resolveResponseType = (requested: ApiResponseType, contentType: string): Exclude<ApiResponseType, 'auto'> => {
  if (requested === 'json' || requested === 'text') {
    return requested;
  }

  const normalized = contentType.toLowerCase();
  if (normalized.includes('application/json') || normalized.includes('+json')) {
    return 'json';
  }

  return 'text';
};

const isAbortError = (error: unknown): boolean => {
  if (!error) {
    return false;
  }

  if (typeof DOMException !== 'undefined' && error instanceof DOMException) {
    return error.name === 'AbortError';
  }

  return error instanceof Error && error.name === 'AbortError';
};

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8001/api';

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(endpoint: string, options: ApiRequestOptions = {}): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const {
      responseType = 'auto',
      timeoutMs,
      signal: externalSignal,
      headers: customHeaders,
      ...restOptions
    } = options;

    const headers = new Headers(customHeaders ?? undefined);
    if (!headers.has('Accept')) {
      headers.set('Accept', 'application/json');
    }
    if (restOptions.body && !headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json');
    }

    let timeoutId: ReturnType<typeof setTimeout> | undefined;
    let abortController: AbortController | undefined;

    if (typeof timeoutMs === 'number') {
      abortController = new AbortController();

      if (externalSignal) {
        if (externalSignal.aborted) {
          abortController.abort();
        } else {
          externalSignal.addEventListener('abort', () => abortController?.abort(), { once: true });
        }
      }

      timeoutId = setTimeout(() => abortController?.abort(), timeoutMs);
    }

    const fetchSignal = abortController ? abortController.signal : externalSignal;

    const config: RequestInit = {
      ...restOptions,
      headers,
      signal: fetchSignal,
    };

    try {
      const response = await fetch(url, config);
      const rawBody = await response.text();
      const contentType = response.headers.get('content-type') ?? '';

      if (!response.ok) {
        let parsedBody: unknown;
        if (rawBody) {
          try {
            parsedBody = JSON.parse(rawBody);
          } catch (parseError) {
            parsedBody = undefined;
          }
        }

        const messageFromBody =
          parsedBody && typeof (parsedBody as { message?: unknown }).message === 'string'
            ? String((parsedBody as { message: string }).message)
            : undefined;

        const errorMessage = messageFromBody ?? getStatusMessage(response.status);

        throw new ApiError({
          message: errorMessage,
          status: response.status,
          body: rawBody || undefined,
          details: parsedBody,
          url,
        });
      }

      if (response.status === 204 || response.status === 205 || !rawBody) {
        return undefined as T;
      }

      const resolvedType = resolveResponseType(responseType, contentType);

      if (resolvedType === 'json') {
        try {
          return JSON.parse(rawBody) as T;
        } catch (parseError) {
          throw new ApiError({
            message: 'Failed to parse JSON response from the server.',
            status: response.status,
            body: rawBody,
            details: parseError instanceof Error ? { message: parseError.message } : undefined,
            url,
          });
        }
      }

      return rawBody as unknown as T;
    } catch (error) {
      if (isAbortError(error)) {
        throw new ApiError({
          message: 'The request was aborted.',
          url,
          isAbortError: true,
          cause: error,
        });
      }

      if (error instanceof ApiError) {
        throw error;
      }

      console.error('API request failed:', error);
      throw new ApiError({
        message: error instanceof Error ? error.message : 'Network request failed.',
        url,
        cause: error,
      });
    } finally {
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
    }
  }

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

export const apiClient = new ApiClient();

export const fetchRequests = (options?: {
  page?: number;
  perPage?: number;
  status?: MediaRequest['status'];
  type?: MediaRequest['type'];
}) => apiClient.getRequests(options);
export const fetchRequest = (id: string) => apiClient.getRequest(id);
export const fetchReleases = (filters?: { status?: Release['status']; requestId?: string }) =>
  apiClient.getReleases(filters);
export const fetchRelease = (id: string) => apiClient.getRelease(id);
export const fetchReleasesByRequest = (requestId: string) => apiClient.getReleasesByRequest(requestId);
export const fetchReleasesByStatus = (status: string) => apiClient.getReleasesByStatus(status);
export const updateReleaseFileMappings = (releaseId: string, mappings: ReleaseFileMappingInput[]) =>
  apiClient.updateReleaseFileMappings(releaseId, mappings);
export const pauseRelease = (id: string) => apiClient.pauseRelease(id);
export const resumeRelease = (id: string) => apiClient.resumeRelease(id);
export const deleteRelease = (id: string) => apiClient.deleteRelease(id);
export const searchReleaseCandidates = (query: string, requestId?: string) =>
  apiClient.searchReleaseCandidates(query, requestId);
export const downloadReleaseCandidate = (
  requestId: string,
  payload: ReleaseDownloadRequest,
) => apiClient.downloadReleaseCandidate(requestId, payload);
export const fetchRequestLogsApi = (requestId?: string) =>
  apiClient.getRequestLogs({ requestId });

export { ApiClient };
