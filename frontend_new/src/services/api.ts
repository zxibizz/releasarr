import type { ZodType } from 'zod';

import type {
  AsyncOperationResponse,
  DownloadReleaseResponse,
  LogsResponse,
  MediaRequest,
  Release,
  ReleaseDownloadRequest,
  ReleaseFileMappingInput,
  ReleaseSearchResponse,
  ReleasesResponse,
  RequestsResponse,
  RequestLogEntry,
} from '@/types';
import {
  asyncOperationResponseSchema,
  logsResponseSchema,
  mediaRequestSchema,
  releaseDownloadRequestSchema,
  releaseFileMappingInputSchema,
  releaseSchema,
  releaseSearchResponseSchema,
  releasesResponseSchema,
  requestsResponseSchema,
  successResponseSchema,
} from '@/types';

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

  constructor({
    message,
    status,
    body,
    details,
    url,
    isAbortError = false,
    cause,
  }: ApiErrorParams) {
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

const resolveResponseType = (
  requested: ApiResponseType,
  contentType: string,
): Exclude<ApiResponseType, 'auto'> => {
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

const API_BASE_URL =
  (import.meta.env.VITE_API_URL as string | undefined) || 'http://localhost:8001/api';

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: ApiRequestOptions = {},
    schema?: ZodType<T>,
  ): Promise<T> {
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
          } catch {
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
        if (schema) {
          throw new ApiError({
            message: 'Expected response body but received none.',
            status: response.status,
            url,
          });
        }
        return undefined as T;
      }

      const resolvedType = resolveResponseType(responseType, contentType);

      if (resolvedType === 'json') {
        let parsed: unknown;
        try {
          parsed = JSON.parse(rawBody);
        } catch (parseError) {
          throw new ApiError({
            message: 'Failed to parse JSON response from the server.',
            status: response.status,
            body: rawBody,
            details: parseError instanceof Error ? { message: parseError.message } : undefined,
            url,
          });
        }

        if (!schema) {
          return parsed as T;
        }

        const validation = schema.safeParse(parsed);
        if (!validation.success) {
          throw new ApiError({
            message: 'Response validation failed.',
            status: response.status,
            body: rawBody,
            details: validation.error.format(),
            url,
          });
        }

        return validation.data;
      }

      if (schema) {
        throw new ApiError({
          message: 'Expected JSON response from the server.',
          status: response.status,
          body: rawBody,
          url,
        });
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

  async getRequests(
    options: {
      page?: number;
      perPage?: number;
      status?: MediaRequest['status'];
      type?: MediaRequest['type'];
    } = {},
  ): Promise<RequestsResponse> {
    const searchParams = new URLSearchParams();
    if (options.page) searchParams.set('page', String(options.page));
    if (options.perPage) searchParams.set('per_page', String(options.perPage));
    if (options.status) searchParams.set('status', options.status);
    if (options.type) searchParams.set('type', options.type);

    const query = searchParams.toString();
    return this.request<RequestsResponse>(
      `/requests${query ? `?${query}` : ''}`,
      undefined,
      requestsResponseSchema,
    );
  }

  async getRequest(id: string): Promise<MediaRequest> {
    return this.request<MediaRequest>(`/requests/${id}`, undefined, mediaRequestSchema);
  }

  async searchReleaseCandidates(query: string, requestId?: string): Promise<ReleaseSearchResponse> {
    const searchParams = new URLSearchParams();
    searchParams.set('q', query);
    if (requestId) {
      searchParams.set('request_id', requestId);
    }
    const endpoint = `/releases/search?${searchParams.toString()}`;
    return this.request<ReleaseSearchResponse>(endpoint, undefined, releaseSearchResponseSchema);
  }

  async createRequest(requestData: Partial<MediaRequest>): Promise<MediaRequest> {
    return this.request<MediaRequest>(
      '/requests',
      {
        method: 'POST',
        body: JSON.stringify(requestData),
      },
      mediaRequestSchema,
    );
  }

  async updateRequest(id: string, requestData: Partial<MediaRequest>): Promise<MediaRequest> {
    return this.request<MediaRequest>(
      `/requests/${id}`,
      {
        method: 'PATCH',
        body: JSON.stringify(requestData),
      },
      mediaRequestSchema,
    );
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
    const validatedPayload = releaseDownloadRequestSchema.parse(payload);
    return this.request<DownloadReleaseResponse>(
      `/requests/${requestId}/releases/download`,
      {
        method: 'POST',
        body: JSON.stringify(validatedPayload),
      },
      asyncOperationResponseSchema,
    );
  }

  async getReleases(
    filters: { status?: Release['status']; requestId?: string } = {},
  ): Promise<Release[]> {
    const searchParams = new URLSearchParams();
    if (filters.status) searchParams.set('status', filters.status);
    if (filters.requestId) searchParams.set('request_id', filters.requestId);
    const query = searchParams.toString();
    const response = await this.request<ReleasesResponse>(
      `/releases${query ? `?${query}` : ''}`,
      undefined,
      releasesResponseSchema,
    );
    return response.releases;
  }

  async getRelease(id: string): Promise<Release> {
    return this.request<Release>(`/releases/${id}`, undefined, releaseSchema);
  }

  async getReleasesByRequest(requestId: string): Promise<Release[]> {
    const response = await this.request<ReleasesResponse>(
      `/requests/${requestId}/releases`,
      undefined,
      releasesResponseSchema,
    );
    return response.releases;
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
    const response = await this.request<LogsResponse>(
      `/logs${query ? `?${query}` : ''}`,
      undefined,
      logsResponseSchema,
    );
    return response.logs;
  }

  async updateReleaseFileMappings(
    releaseId: string,
    mappings: ReleaseFileMappingInput[],
  ): Promise<boolean> {
    const files = releaseFileMappingInputSchema.array().parse(mappings);
    const response = await this.request(
      `/releases/${releaseId}/files/mapping`,
      {
        method: 'PUT',
        body: JSON.stringify({ files }),
      },
      successResponseSchema,
    );
    return response.success;
  }

  async pauseRelease(id: string): Promise<AsyncOperationResponse> {
    return this.request<AsyncOperationResponse>(
      `/releases/${id}/pause`,
      {
        method: 'POST',
      },
      asyncOperationResponseSchema,
    );
  }

  async resumeRelease(id: string): Promise<AsyncOperationResponse> {
    return this.request<AsyncOperationResponse>(
      `/releases/${id}/resume`,
      {
        method: 'POST',
      },
      asyncOperationResponseSchema,
    );
  }

  async deleteRelease(id: string): Promise<void> {
    return this.request<void>(`/releases/${id}`, {
      method: 'DELETE',
    });
  }

  async addRelease(releaseData: { magnet_link: string; request_ids: string[] }): Promise<Release> {
    return this.request<Release>(
      '/releases',
      {
        method: 'POST',
        body: JSON.stringify(releaseData),
      },
      releaseSchema,
    );
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
export const fetchReleasesByRequest = (requestId: string) =>
  apiClient.getReleasesByRequest(requestId);
export const fetchReleasesByStatus = (status: string) => apiClient.getReleasesByStatus(status);
export const updateReleaseFileMappings = (releaseId: string, mappings: ReleaseFileMappingInput[]) =>
  apiClient.updateReleaseFileMappings(releaseId, mappings);
export const pauseRelease = (id: string) => apiClient.pauseRelease(id);
export const resumeRelease = (id: string) => apiClient.resumeRelease(id);
export const deleteRelease = (id: string) => apiClient.deleteRelease(id);
export const searchReleaseCandidates = (query: string, requestId?: string) =>
  apiClient.searchReleaseCandidates(query, requestId);
export const downloadReleaseCandidate = (requestId: string, payload: ReleaseDownloadRequest) =>
  apiClient.downloadReleaseCandidate(requestId, payload);
export const fetchRequestLogsApi = (requestId?: string) => apiClient.getRequestLogs({ requestId });

export { ApiClient };
