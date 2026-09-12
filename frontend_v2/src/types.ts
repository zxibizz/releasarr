import type { components } from './lib/api/generated/types';

type Schemas = components['schemas'];

export type MediaType = Schemas['MediaType'];
export type MediaRequestStatus = Schemas['MediaRequestStatus'];
export type MediaRequest = Schemas['MediaRequest'];
export type MovieRequest = Schemas['MovieRequest'];
export type SeriesRequest = Schemas['SeriesRequest'];
export type RequestsResponse = Schemas['RequestsResponse'];

export type ReleaseStatus = Schemas['ReleaseStatus'];
export type Release = Schemas['Release'];
export type ReleasesResponse = Schemas['ReleasesResponse'];
export type ReleaseFile = Schemas['ReleaseFile'];
export type ReleaseSearchResult = Schemas['ReleaseSearchResult'];
export type ReleaseSearchResponse = Schemas['ReleaseSearchResponse'];
export type ReleaseDownloadRequest = Schemas['ReleaseDownloadRequest'];

export type FileRequestMapping = Schemas['FileRequestMapping'];
export type MovieFileRequestMapping = Schemas['MovieFileRequestMapping'];
export type SeriesFileRequestMapping = Schemas['SeriesFileRequestMapping'];
export type ReleaseFileMappingInput = Schemas['ReleaseFileMappingInput'];

export type AsyncOperationResponse = Schemas['AsyncOperationResponse'];
export type SuccessResponse = Schemas['SuccessResponse'];

export type RequestLogLevel = Schemas['RequestLogLevel'];
export type RequestLogEntry = Schemas['RequestLogEntry'];
export type LogsResponse = Schemas['LogsResponse'];
