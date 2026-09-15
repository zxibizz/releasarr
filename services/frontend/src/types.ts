import type { components } from './lib/api/generated/types';

type Schemas = components['schemas'];

export type MediaType = Schemas['MediaType'];
export type MediaRequestStatus = Schemas['MediaRequestStatus'];
export type MediaRequest = Schemas['MediaRequest'];
export type MovieRequest = Schemas['MovieRequest'];
export type SeriesRequest = Schemas['SeriesRequest'];
export type RequestsResponse = Schemas['RequestsResponse'];
export type RequestWarning = Schemas['RequestWarning'];
export type RequestWarningCode = Schemas['RequestWarningCode'];
export type EpisodeStatus = Schemas['EpisodeStatus'];
export type SeasonEpisode = Schemas['SeasonEpisode'];
export type SeasonEpisodesResponse = Schemas['SeasonEpisodesResponse'];

export type ReleaseStatus = Schemas['ReleaseStatus'];
export type Release = Schemas['Release'];
export type ReleasesResponse = Schemas['ReleasesResponse'];
export type ReleaseFile = Schemas['ReleaseFile'];
export type ReleaseWarning = Schemas['ReleaseWarning'];
export type ReleaseSearchResult = Schemas['ReleaseSearchResult'];
export type ReleaseSearchResponse = Schemas['ReleaseSearchResponse'];
export type IndexerSearchFailure = Schemas['IndexerSearchFailure'];
export type ReleaseDownloadRequest = Schemas['ReleaseDownloadRequest'];
export type ManualReleaseRequest = Schemas['ManualReleaseRequest'];
export type ExistingReleasesAction = Schemas['ExistingReleasesAction'];

export type MediaSearchResult = Schemas['MediaSearchResult'];
export type MediaSearchResponse = Schemas['MediaSearchResponse'];
export type SeasonOption = Schemas['SeasonOption'];
export type SeriesSeasonsResponse = Schemas['SeriesSeasonsResponse'];
export type RootFolder = Schemas['RootFolder'];
export type RootFoldersResponse = Schemas['RootFoldersResponse'];
export type AddRequestPayload = Schemas['AddRequestPayload'];
export type AddRequestResponse = Schemas['AddRequestResponse'];
export type UpdateSeasonsPayload = Schemas['UpdateSeasonsPayload'];

export type FileRequestMapping = Schemas['FileRequestMapping'];
export type MovieFileRequestMapping = Schemas['MovieFileRequestMapping'];
export type SeriesFileRequestMapping = Schemas['SeriesFileRequestMapping'];
export type ReleaseFileMappingInput = Schemas['ReleaseFileMappingInput'];
export type ReleaseFileMappingSuggestion = Schemas['ReleaseFileMappingSuggestion'];
export type ReleaseFileMappingSuggestions = Schemas['ReleaseFileMappingSuggestions'];

export type AsyncOperationResponse = Schemas['AsyncOperationResponse'];
export type SuccessResponse = Schemas['SuccessResponse'];

export type RequestLogLevel = Schemas['RequestLogLevel'];
export type RequestLogEntry = Schemas['RequestLogEntry'];
export type LogsResponse = Schemas['LogsResponse'];
export type LogService = Schemas['LogService'];

export type SyncJobKind = Schemas['SyncJobKind'];
export type SyncJobStatus = Schemas['SyncJobStatus'];
export type SyncJobTrigger = Schemas['SyncJobTrigger'];
export type SyncJob = Schemas['SyncJob'];
export type SyncJobsResponse = Schemas['SyncJobsResponse'];
export type ScheduledTask = Schemas['ScheduledTask'];
export type ScheduledTasksResponse = Schemas['ScheduledTasksResponse'];

export type IndexerHealth = Schemas['IndexerHealth'];
export type Indexer = Schemas['Indexer'];
export type IndexersResponse = Schemas['IndexersResponse'];
export type IndexerTestResult = Schemas['IndexerTestResult'];
export type IndexerTestResults = Schemas['IndexerTestResults'];
export type IndexerEventType = Schemas['IndexerEventType'];
export type IndexerHistoryEntry = Schemas['IndexerHistoryEntry'];
export type IndexerHistoryResponse = Schemas['IndexerHistoryResponse'];
export type IndexerLogLevel = Schemas['IndexerLogLevel'];
export type IndexerLogEntry = Schemas['IndexerLogEntry'];
export type IndexerLogsResponse = Schemas['IndexerLogsResponse'];

export type UserRole = Schemas['UserRole'];
export type User = Schemas['User'];
export type SessionUser = Schemas['SessionUser'];
export type UsersResponse = Schemas['UsersResponse'];
export type CreateUserPayload = Schemas['CreateUserPayload'];
export type UpdateUserPayload = Schemas['UpdateUserPayload'];
export type ChangePasswordPayload = Schemas['ChangePasswordPayload'];
export type ServiceApiKey = Schemas['ServiceApiKey'];

export type SetupStatus = Schemas['SetupStatus'];
export type SetupPayload = Schemas['SetupPayload'];
export type LoginPayload = Schemas['LoginPayload'];
export type LoginResponse = Schemas['LoginResponse'];
