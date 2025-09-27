import { makeApi, Zodios, type ZodiosOptions } from '@zodios/core';
import { z } from 'zod';

const MediaRequestStatus = z.enum(['pending', 'searching', 'downloading', 'completed', 'failed']);
const MediaLocalization = z
  .object({ title: z.string().nullable(), overview: z.string().nullable() })
  .partial();
const BaseMediaRequest = z
  .object({
    id: z.string(),
    title: z.string(),
    year: z.number().int(),
    poster_url: z.string().url(),
    overview: z.string(),
    genres: z.array(z.string()),
    status: MediaRequestStatus,
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    localizations: z.record(MediaLocalization).optional(),
  })
  .passthrough();
const MovieRequest = BaseMediaRequest.merge(
  z
    .object({ type: z.literal('movie'), runtime: z.number().int(), imdb_id: z.string() })
    .passthrough(),
);
const SeriesRequest = BaseMediaRequest.merge(
  z
    .object({
      type: z.literal('series'),
      season_number: z.number().int(),
      total_episodes: z.number().int(),
      series_title: z.string(),
      series_year: z.number().int(),
      imdb_id: z.string(),
      sonarr_series_id: z.number().int().nullish(),
    })
    .passthrough(),
);
const MediaRequest = z.discriminatedUnion('type', [MovieRequest, SeriesRequest]);
const RequestsResponse = z
  .object({
    requests: z.array(MediaRequest),
    total: z.number().int().gte(0),
    page: z.number().int().gte(1),
    per_page: z.number().int().gte(1),
  })
  .passthrough();
const ErrorResponse = z
  .object({
    code: z.string(),
    message: z.string(),
    details: z
      .record(z.union([z.string(), z.number(), z.boolean(), z.array(z.string())]))
      .optional(),
  })
  .passthrough();
const CreateMovieRequest = z
  .object({
    type: z.literal('movie'),
    title: z.string(),
    year: z.number().int(),
    runtime: z.number().int(),
    imdb_id: z.string(),
    overview: z.string().optional(),
    poster_url: z.string().optional(),
    genres: z.array(z.string()).optional(),
    localizations: z.record(MediaLocalization).optional(),
  })
  .passthrough();
const CreateSeriesRequest = z
  .object({
    type: z.literal('series'),
    title: z.string(),
    year: z.number().int(),
    season_number: z.number().int(),
    total_episodes: z.number().int(),
    series_title: z.string(),
    series_year: z.number().int(),
    imdb_id: z.string(),
    overview: z.string().optional(),
    poster_url: z.string().optional(),
    genres: z.array(z.string()).optional(),
    localizations: z.record(MediaLocalization).optional(),
  })
  .passthrough();
const MediaRequestCreate = z.discriminatedUnion('type', [CreateMovieRequest, CreateSeriesRequest]);
const MediaRequestUpdate = z
  .object({
    title: z.string().nullable(),
    year: z.number().int().nullable(),
    poster_url: z.string().nullable(),
    overview: z.string().nullable(),
    genres: z.array(z.string()).nullable(),
    status: MediaRequestStatus,
    runtime: z.number().int().nullable(),
    imdb_id: z.string().nullable(),
    season_number: z.number().int().nullable(),
    total_episodes: z.number().int().nullable(),
    series_title: z.string().nullable(),
    series_year: z.number().int().nullable(),
    localizations: z.record(MediaLocalization).nullable(),
  })
  .partial()
  .passthrough();
const MovieFileRequestMapping = z
  .object({
    request_id: z.string(),
    request_title: z.string().optional(),
    mapping_type: z.literal('movie'),
  })
  .passthrough();
const SeriesFileRequestMapping = z
  .object({
    request_id: z.string(),
    request_title: z.string().optional(),
    mapping_type: z.literal('series'),
    season: z.number().int().gte(1),
    episode: z.number().int().gte(1),
  })
  .passthrough();
const FileRequestMapping = z.discriminatedUnion('mapping_type', [
  MovieFileRequestMapping,
  SeriesFileRequestMapping,
]);
const ReleaseFile = z
  .object({
    id: z.string(),
    name: z.string(),
    size: z.number().int(),
    path: z.string(),
    request_mapping: FileRequestMapping.optional(),
  })
  .passthrough();
const ReleaseStatus = z.enum(['pending', 'downloading', 'seeding', 'completed', 'failed']);
const Release = z
  .object({
    id: z.string(),
    name: z.string(),
    hash: z.string(),
    size: z.number().int(),
    files: z.array(ReleaseFile),
    status: ReleaseStatus,
    progress: z.number().gte(0).lte(100),
    download_speed: z.number(),
    upload_speed: z.number(),
    seeders: z.number().int(),
    leechers: z.number().int(),
    ratio: z.number(),
    added_date: z.string().datetime({ offset: true }),
    completed_date: z.string().datetime({ offset: true }).optional(),
    request_ids: z.array(z.string()),
    torrent_source: z.string().optional(),
    quality: z.string().optional(),
  })
  .passthrough();
const ReleasesResponse = z
  .object({
    releases: z.array(Release),
    total: z.number().int().gte(0),
    page: z.number().int().gte(1),
    per_page: z.number().int().gte(1),
  })
  .passthrough();
const AddReleaseRequest = z
  .object({ magnet_link: z.string(), request_ids: z.array(z.string()) })
  .passthrough();
const AsyncOperationResponse = z
  .object({
    operation: z.string(),
    status: z.enum(['queued', 'pending']),
    operation_id: z.string().optional(),
    location: z.string().url().nullish(),
    message: z.string().nullish(),
    resource_id: z.string().nullish(),
    details: z.object({}).partial().passthrough().nullish(),
  })
  .passthrough();
const ReleaseFileMappingInput = z
  .object({ file_id: z.string(), request_mapping: FileRequestMapping.optional() })
  .passthrough();
const ReleaseFileMappingsUpdate = z
  .object({ files: z.array(ReleaseFileMappingInput) })
  .passthrough();
const SuccessResponse = z.object({ success: z.boolean() }).passthrough();
const ReleaseSearchResult = z
  .object({
    release_id: z.string(),
    release_name: z.string(),
    size: z.string(),
    magnet_link: z.string().url().optional(),
    torrent_file_url: z.string().url().optional(),
    info_url: z.string().url().optional(),
    seeders: z.number().int().gte(0).optional(),
    leechers: z.number().int().gte(0).optional(),
    quality: z.string().optional(),
    source: z.string().optional(),
    request_id: z.string().optional(),
  })
  .passthrough();
const ReleaseSearchResponse = z
  .object({
    results: z.array(ReleaseSearchResult),
    query: z.string(),
    total_results: z.number().int(),
  })
  .passthrough();
const ReleaseDownloadRequest = z.object({ release_id: z.string() }).passthrough();
const RequestLogLevel = z.enum(['info', 'warning', 'error']);
const RequestLogMetadata = z.record(z.union([z.string(), z.number(), z.boolean()]));
const RequestLogEntry = z
  .object({
    id: z.string(),
    occurredAt: z.number().int(),
    timestamp: z.string(),
    level: RequestLogLevel,
    message: z.string(),
    source: z.string().optional(),
    metadata: RequestLogMetadata.optional(),
    stackTrace: z.string().optional(),
  })
  .passthrough();
const LogsResponse = z
  .object({
    logs: z.array(RequestLogEntry),
    total: z.number().int().gte(0),
    page: z.number().int().gte(1),
    per_page: z.number().int().gte(1),
  })
  .passthrough();
const MediaType = z.enum(['movie', 'series']);

export const schemas = {
  MediaRequestStatus,
  MediaLocalization,
  BaseMediaRequest,
  MovieRequest,
  SeriesRequest,
  MediaRequest,
  RequestsResponse,
  ErrorResponse,
  CreateMovieRequest,
  CreateSeriesRequest,
  MediaRequestCreate,
  MediaRequestUpdate,
  MovieFileRequestMapping,
  SeriesFileRequestMapping,
  FileRequestMapping,
  ReleaseFile,
  ReleaseStatus,
  Release,
  ReleasesResponse,
  AddReleaseRequest,
  AsyncOperationResponse,
  ReleaseFileMappingInput,
  ReleaseFileMappingsUpdate,
  SuccessResponse,
  ReleaseSearchResult,
  ReleaseSearchResponse,
  ReleaseDownloadRequest,
  RequestLogLevel,
  RequestLogMetadata,
  RequestLogEntry,
  LogsResponse,
  MediaType,
};

const endpoints = makeApi([
  {
    method: 'get',
    path: '/logs',
    alias: 'listRequestLogs',
    requestFormat: 'json',
    parameters: [
      {
        name: 'page',
        type: 'Query',
        schema: z.number().int().gte(1).optional(),
      },
      {
        name: 'per_page',
        type: 'Query',
        schema: z.number().int().gte(1).lte(100).optional(),
      },
      {
        name: 'request_id',
        type: 'Query',
        schema: z.string().optional(),
      },
    ],
    response: LogsResponse,
    errors: [
      {
        status: 400,
        description: `Invalid pagination or filter parameters.`,
        schema: ErrorResponse,
      },
      {
        status: 500,
        description: `Unexpected server error.`,
        schema: ErrorResponse,
      },
    ],
  },
  {
    method: 'get',
    path: '/releases',
    alias: 'listReleases',
    requestFormat: 'json',
    parameters: [
      {
        name: 'page',
        type: 'Query',
        schema: z.number().int().gte(1).optional(),
      },
      {
        name: 'per_page',
        type: 'Query',
        schema: z.number().int().gte(1).lte(100).optional(),
      },
      {
        name: 'status',
        type: 'Query',
        schema: z.enum(['pending', 'downloading', 'seeding', 'completed', 'failed']).optional(),
      },
      {
        name: 'request_id',
        type: 'Query',
        schema: z.string().optional(),
      },
    ],
    response: ReleasesResponse,
    errors: [
      {
        status: 400,
        description: `Invalid pagination or filter parameters.`,
        schema: ErrorResponse,
      },
      {
        status: 500,
        description: `Unexpected server error.`,
        schema: ErrorResponse,
      },
    ],
  },
  {
    method: 'post',
    path: '/releases',
    alias: 'createRelease',
    requestFormat: 'json',
    parameters: [
      {
        name: 'body',
        type: 'Body',
        schema: AddReleaseRequest,
      },
    ],
    response: Release,
    errors: [
      {
        status: 400,
        description: `Malformed request payload.`,
        schema: ErrorResponse,
      },
      {
        status: 409,
        description: `A release with the same identifier already exists.`,
        schema: ErrorResponse,
      },
      {
        status: 422,
        description: `Validation failed for the provided fields.`,
        schema: ErrorResponse,
      },
      {
        status: 500,
        description: `Unexpected server error.`,
        schema: ErrorResponse,
      },
    ],
  },
  {
    method: 'get',
    path: '/releases/:releaseId',
    alias: 'getRelease',
    requestFormat: 'json',
    parameters: [
      {
        name: 'releaseId',
        type: 'Path',
        schema: z.string(),
      },
    ],
    response: Release,
    errors: [
      {
        status: 404,
        description: `Release not found.`,
        schema: ErrorResponse,
      },
      {
        status: 500,
        description: `Unexpected server error.`,
        schema: ErrorResponse,
      },
    ],
  },
  {
    method: 'delete',
    path: '/releases/:releaseId',
    alias: 'deleteRelease',
    requestFormat: 'json',
    parameters: [
      {
        name: 'releaseId',
        type: 'Path',
        schema: z.string(),
      },
    ],
    response: z.void(),
    errors: [
      {
        status: 404,
        description: `Release not found.`,
        schema: ErrorResponse,
      },
      {
        status: 500,
        description: `Unexpected server error.`,
        schema: ErrorResponse,
      },
    ],
  },
  {
    method: 'put',
    path: '/releases/:releaseId/files/mapping',
    alias: 'updateReleaseFileMappings',
    requestFormat: 'json',
    parameters: [
      {
        name: 'body',
        type: 'Body',
        schema: ReleaseFileMappingsUpdate,
      },
      {
        name: 'releaseId',
        type: 'Path',
        schema: z.string(),
      },
    ],
    response: z.object({ success: z.boolean() }).passthrough(),
    errors: [
      {
        status: 400,
        description: `Malformed request payload.`,
        schema: ErrorResponse,
      },
      {
        status: 404,
        description: `Release or file not found.`,
        schema: ErrorResponse,
      },
      {
        status: 500,
        description: `Unexpected server error.`,
        schema: ErrorResponse,
      },
    ],
  },
  {
    method: 'post',
    path: '/releases/:releaseId/pause',
    alias: 'pauseRelease',
    requestFormat: 'json',
    parameters: [
      {
        name: 'releaseId',
        type: 'Path',
        schema: z.string(),
      },
    ],
    response: AsyncOperationResponse,
    errors: [
      {
        status: 400,
        description: `Release cannot be paused because the request was invalid.`,
        schema: ErrorResponse,
      },
      {
        status: 404,
        description: `Release not found.`,
        schema: ErrorResponse,
      },
      {
        status: 409,
        description: `Release is not in a pausable state.`,
        schema: ErrorResponse,
      },
      {
        status: 500,
        description: `Unexpected server error.`,
        schema: ErrorResponse,
      },
    ],
  },
  {
    method: 'post',
    path: '/releases/:releaseId/resume',
    alias: 'resumeRelease',
    requestFormat: 'json',
    parameters: [
      {
        name: 'releaseId',
        type: 'Path',
        schema: z.string(),
      },
    ],
    response: AsyncOperationResponse,
    errors: [
      {
        status: 400,
        description: `Release cannot be resumed because the request was invalid.`,
        schema: ErrorResponse,
      },
      {
        status: 404,
        description: `Release not found.`,
        schema: ErrorResponse,
      },
      {
        status: 409,
        description: `Release is not in a resumable state.`,
        schema: ErrorResponse,
      },
      {
        status: 500,
        description: `Unexpected server error.`,
        schema: ErrorResponse,
      },
    ],
  },
  {
    method: 'get',
    path: '/releases/search',
    alias: 'searchReleaseSources',
    requestFormat: 'json',
    parameters: [
      {
        name: 'q',
        type: 'Query',
        schema: z.string(),
      },
      {
        name: 'request_id',
        type: 'Query',
        schema: z.string().optional(),
      },
    ],
    response: ReleaseSearchResponse,
    errors: [
      {
        status: 400,
        description: `Malformed search query.`,
        schema: ErrorResponse,
      },
      {
        status: 500,
        description: `Unexpected server error.`,
        schema: ErrorResponse,
      },
    ],
  },
  {
    method: 'get',
    path: '/requests',
    alias: 'listRequests',
    requestFormat: 'json',
    parameters: [
      {
        name: 'page',
        type: 'Query',
        schema: z.number().int().gte(1).optional(),
      },
      {
        name: 'per_page',
        type: 'Query',
        schema: z.number().int().gte(1).lte(100).optional(),
      },
      {
        name: 'status',
        type: 'Query',
        schema: z.enum(['pending', 'searching', 'downloading', 'completed', 'failed']).optional(),
      },
      {
        name: 'type',
        type: 'Query',
        schema: z.enum(['movie', 'series']).optional(),
      },
    ],
    response: RequestsResponse,
    errors: [
      {
        status: 400,
        description: `Invalid pagination or filter parameters.`,
        schema: ErrorResponse,
      },
      {
        status: 500,
        description: `Unexpected server error.`,
        schema: ErrorResponse,
      },
    ],
  },
  {
    method: 'post',
    path: '/requests',
    alias: 'createRequest',
    requestFormat: 'json',
    parameters: [
      {
        name: 'body',
        type: 'Body',
        schema: MediaRequestCreate,
      },
    ],
    response: MediaRequest,
    errors: [
      {
        status: 400,
        description: `Malformed request payload.`,
        schema: ErrorResponse,
      },
      {
        status: 422,
        description: `Validation failed for the provided fields.`,
        schema: ErrorResponse,
      },
      {
        status: 500,
        description: `Unexpected server error.`,
        schema: ErrorResponse,
      },
    ],
  },
  {
    method: 'get',
    path: '/requests/:requestId',
    alias: 'getRequest',
    requestFormat: 'json',
    parameters: [
      {
        name: 'requestId',
        type: 'Path',
        schema: z.string(),
      },
    ],
    response: MediaRequest,
    errors: [
      {
        status: 404,
        description: `Request not found.`,
        schema: ErrorResponse,
      },
      {
        status: 500,
        description: `Unexpected server error.`,
        schema: ErrorResponse,
      },
    ],
  },
  {
    method: 'patch',
    path: '/requests/:requestId',
    alias: 'updateRequest',
    requestFormat: 'json',
    parameters: [
      {
        name: 'body',
        type: 'Body',
        schema: MediaRequestUpdate,
      },
      {
        name: 'requestId',
        type: 'Path',
        schema: z.string(),
      },
    ],
    response: MediaRequest,
    errors: [
      {
        status: 400,
        description: `Malformed request body.`,
        schema: ErrorResponse,
      },
      {
        status: 404,
        description: `Request not found.`,
        schema: ErrorResponse,
      },
      {
        status: 422,
        description: `Validation failed for at least one field.`,
        schema: ErrorResponse,
      },
      {
        status: 500,
        description: `Unexpected server error.`,
        schema: ErrorResponse,
      },
    ],
  },
  {
    method: 'delete',
    path: '/requests/:requestId',
    alias: 'deleteRequest',
    requestFormat: 'json',
    parameters: [
      {
        name: 'requestId',
        type: 'Path',
        schema: z.string(),
      },
    ],
    response: z.void(),
    errors: [
      {
        status: 404,
        description: `Request not found.`,
        schema: ErrorResponse,
      },
      {
        status: 500,
        description: `Unexpected server error.`,
        schema: ErrorResponse,
      },
    ],
  },
  {
    method: 'post',
    path: '/requests/:requestId/releases/download',
    alias: 'queueReleaseDownload',
    requestFormat: 'json',
    parameters: [
      {
        name: 'body',
        type: 'Body',
        schema: z.object({ release_id: z.string() }).passthrough(),
      },
      {
        name: 'requestId',
        type: 'Path',
        schema: z.string(),
      },
    ],
    response: AsyncOperationResponse,
    errors: [
      {
        status: 400,
        description: `Malformed request body.`,
        schema: ErrorResponse,
      },
      {
        status: 404,
        description: `Release candidate not found for the request.`,
        schema: ErrorResponse,
      },
      {
        status: 409,
        description: `Request already has an active download.`,
        schema: ErrorResponse,
      },
      {
        status: 500,
        description: `Unexpected server error.`,
        schema: ErrorResponse,
      },
    ],
  },
]);

export const api = new Zodios(endpoints);

export function createApiClient(baseUrl: string, options?: ZodiosOptions) {
  return new Zodios(baseUrl, endpoints, options);
}
