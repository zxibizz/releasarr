import type { AsyncOperationResponse, ReleaseSearchResult } from './releases.schema';

export {
  mediaTypeSchema,
  mediaRequestStatusSchema,
  mediaRequestSchema,
  requestsResponseSchema,
  mediaRequestUpdateSchema,
  mediaRequestCreateSchema,
  requestsQuerySchema,
  baseRequestSchema,
  movieRequestSchema,
  seriesRequestSchema,
} from './requests.schema';
export type {
  MediaType,
  MediaRequestStatus,
  MediaRequest,
  RequestsResponse,
  MediaRequestUpdate,
  MediaRequestCreate,
  RequestsQuery,
  BaseRequest,
  MovieRequest,
  SeriesRequest,
} from './requests.schema';

export {
  releaseStatusSchema,
  movieFileRequestMappingSchema,
  seriesFileRequestMappingSchema,
  fileRequestMappingSchema,
  releaseFileSchema,
  releaseSchema,
  releasesResponseSchema,
  releaseSearchResultSchema,
  releaseSearchResponseSchema,
  releaseDownloadRequestSchema,
  asyncOperationResponseSchema,
  successResponseSchema,
  releaseFileMappingInputSchema,
} from './releases.schema';
export type {
  ReleaseStatus,
  FileRequestMapping,
  ReleaseFile,
  Release,
  ReleasesResponse,
  ReleaseSearchResult,
  ReleaseSearchResponse,
  ReleaseDownloadRequest,
  AsyncOperationResponse,
  SuccessResponse,
  ReleaseFileMappingInput,
  MovieFileRequestMapping,
  SeriesFileRequestMapping,
} from './releases.schema';

export {
  requestLogLevelSchema,
  requestLogEntrySchema,
  logsResponseSchema,
  requestLogMetadataSchema,
} from './logs';
export type { RequestLogLevel, RequestLogEntry, LogsResponse, RequestLogMetadata } from './logs';

export interface ReleaseSearchState {
  query: string;
  results: ReleaseSearchResult[];
  loading: boolean;
  error: string | null;
}

export type DownloadReleaseResponse = AsyncOperationResponse;
