import { z } from 'zod';

import { schemas as generatedSchemas } from '../generated/releasarr';
import type { components } from '../generated/releasarr-types';

type Schemas = components['schemas'];

type MediaRequests = Schemas['MediaRequest'];
type Releases = Schemas['Release'];
type ReleaseSearchResults = Schemas['ReleaseSearchResult'];
type RequestLogs = Schemas['RequestLogEntry'];

type SchemaRegistry = typeof generatedSchemas;

export const schemas: SchemaRegistry = generatedSchemas;

export const mediaTypeSchema = schemas.MediaType;
export type MediaType = Schemas['MediaType'];

export const mediaRequestStatusSchema = schemas.MediaRequestStatus;
export type MediaRequestStatus = Schemas['MediaRequestStatus'];

export const baseRequestSchema = schemas.BaseMediaRequest;
export type BaseRequest = Schemas['BaseMediaRequest'];

export const movieRequestSchema = schemas.MovieRequest;
export type MovieRequest = Schemas['MovieRequest'];

export const seriesRequestSchema = schemas.SeriesRequest;
export type SeriesRequest = Schemas['SeriesRequest'];

export const mediaRequestSchema = schemas.MediaRequest;
export type MediaRequest = MediaRequests;

export const requestsResponseSchema = schemas.RequestsResponse;
export type RequestsResponse = Schemas['RequestsResponse'];

export const mediaRequestUpdateSchema = schemas.MediaRequestUpdate;
export type MediaRequestUpdate = Schemas['MediaRequestUpdate'];

export const mediaRequestCreateSchema = schemas.MediaRequestCreate;
export type MediaRequestCreate = Schemas['MediaRequestCreate'];

export const requestsQuerySchema = z.object({
  page: z.number().int().min(1).optional(),
  per_page: z.number().int().min(1).optional(),
  status: mediaRequestStatusSchema.optional(),
  type: mediaTypeSchema.optional(),
});
export type RequestsQuery = z.infer<typeof requestsQuerySchema>;

export const releaseStatusSchema = schemas.ReleaseStatus;
export type ReleaseStatus = Schemas['ReleaseStatus'];

export const movieFileRequestMappingSchema = schemas.MovieFileRequestMapping;
export type MovieFileRequestMapping = Schemas['MovieFileRequestMapping'];

export const seriesFileRequestMappingSchema = schemas.SeriesFileRequestMapping;
export type SeriesFileRequestMapping = Schemas['SeriesFileRequestMapping'];

export const fileRequestMappingSchema = schemas.FileRequestMapping;
export type FileRequestMapping = Schemas['FileRequestMapping'];

export const releaseFileSchema = schemas.ReleaseFile;
export type ReleaseFile = Schemas['ReleaseFile'];

export const releaseSchema = schemas.Release;
export type Release = Releases;

export const releasesResponseSchema = schemas.ReleasesResponse;
export type ReleasesResponse = Schemas['ReleasesResponse'];

export const releaseSearchResultSchema = schemas.ReleaseSearchResult;
export type ReleaseSearchResult = ReleaseSearchResults;

export const releaseSearchResponseSchema = schemas.ReleaseSearchResponse;
export type ReleaseSearchResponse = Schemas['ReleaseSearchResponse'];

export const releaseDownloadRequestSchema = schemas.ReleaseDownloadRequest;
export type ReleaseDownloadRequest = Schemas['ReleaseDownloadRequest'];

export const asyncOperationResponseSchema = schemas.AsyncOperationResponse;
export type AsyncOperationResponse = Schemas['AsyncOperationResponse'];

export const successResponseSchema = schemas.SuccessResponse;
export type SuccessResponse = Schemas['SuccessResponse'];

export const releaseFileMappingInputSchema = schemas.ReleaseFileMappingInput;
export type ReleaseFileMappingInput = Schemas['ReleaseFileMappingInput'];

export const requestLogLevelSchema = schemas.RequestLogLevel;
export type RequestLogLevel = Schemas['RequestLogLevel'];

export const requestLogMetadataSchema = schemas.RequestLogMetadata;
export type RequestLogMetadata = Schemas['RequestLogMetadata'];

export const requestLogEntrySchema = schemas.RequestLogEntry;
export type RequestLogEntry = RequestLogs;

export const logsResponseSchema = schemas.LogsResponse;
export type LogsResponse = Schemas['LogsResponse'];

export interface ReleaseSearchState {
  query: string;
  results: ReleaseSearchResult[];
  loading: boolean;
  error: string | null;
}

export type DownloadReleaseResponse = AsyncOperationResponse;
