import { z } from 'zod';

export const releaseStatusSchema = z.enum([
  'pending',
  'downloading',
  'seeding',
  'completed',
  'failed',
]);
export type ReleaseStatus = z.infer<typeof releaseStatusSchema>;

export const movieFileRequestMappingSchema = z.object({
  request_id: z.string(),
  request_title: z.string().optional(),
  mapping_type: z.literal('movie'),
});
export type MovieFileRequestMapping = z.infer<typeof movieFileRequestMappingSchema>;

export const seriesFileRequestMappingSchema = z.object({
  request_id: z.string(),
  request_title: z.string().optional(),
  mapping_type: z.literal('series'),
  season: z.number().int().min(1),
  episode: z.number().int().min(1),
});
export type SeriesFileRequestMapping = z.infer<typeof seriesFileRequestMappingSchema>;

export const fileRequestMappingSchema = z.union([
  movieFileRequestMappingSchema,
  seriesFileRequestMappingSchema,
]);
export type FileRequestMapping = z.infer<typeof fileRequestMappingSchema>;

export const releaseFileSchema = z.object({
  id: z.string(),
  name: z.string(),
  size: z.number().int().nonnegative(),
  path: z.string(),
  request_mapping: fileRequestMappingSchema.optional(),
});
export type ReleaseFile = z.infer<typeof releaseFileSchema>;

export const releaseSchema = z.object({
  id: z.string(),
  name: z.string(),
  hash: z.string(),
  size: z.number().int().nonnegative(),
  files: z.array(releaseFileSchema),
  status: releaseStatusSchema,
  progress: z.number().min(0).max(100),
  download_speed: z.number(),
  upload_speed: z.number(),
  seeders: z.number().int().nonnegative(),
  leechers: z.number().int().nonnegative(),
  ratio: z.number(),
  added_date: z.string(),
  completed_date: z.string().optional(),
  request_ids: z.array(z.string()),
  torrent_source: z.string().optional(),
  quality: z.string().optional(),
});
export type Release = z.infer<typeof releaseSchema>;

export const releasesResponseSchema = z.object({
  releases: z.array(releaseSchema),
  total: z.number().int().nonnegative(),
  page: z.number().int().min(1),
  per_page: z.number().int().min(1),
});
export type ReleasesResponse = z.infer<typeof releasesResponseSchema>;

export const releaseSearchResultSchema = z.object({
  release_id: z.string(),
  release_name: z.string(),
  size: z.string(),
  magnet_link: z.string().optional(),
  torrent_file_url: z.string().optional(),
  info_url: z.string().optional(),
  seeders: z.number().int().nonnegative().optional(),
  leechers: z.number().int().nonnegative().optional(),
  quality: z.string().optional(),
  source: z.string().optional(),
  request_id: z.string().optional(),
});
export type ReleaseSearchResult = z.infer<typeof releaseSearchResultSchema>;

export const releaseSearchResponseSchema = z.object({
  results: z.array(releaseSearchResultSchema),
  query: z.string(),
  total_results: z.number().int().nonnegative(),
});
export type ReleaseSearchResponse = z.infer<typeof releaseSearchResponseSchema>;

export const releaseDownloadRequestSchema = z.object({
  release_id: z.string(),
});
export type ReleaseDownloadRequest = z.infer<typeof releaseDownloadRequestSchema>;

export const asyncOperationResponseSchema = z.object({
  operation: z.string(),
  status: z.enum(['queued', 'pending']),
  operation_id: z.string().optional(),
  location: z.string().url().nullable().optional(),
  message: z.string().nullable().optional(),
  resource_id: z.string().nullable().optional(),
  details: z.record(z.any()).nullable().optional(),
});
export type AsyncOperationResponse = z.infer<typeof asyncOperationResponseSchema>;

export const successResponseSchema = z.object({
  success: z.boolean(),
});
export type SuccessResponse = z.infer<typeof successResponseSchema>;

export const releaseFileMappingInputSchema = z.object({
  file_id: z.string(),
  request_mapping: fileRequestMappingSchema.optional(),
});
export type ReleaseFileMappingInput = z.infer<typeof releaseFileMappingInputSchema>;
