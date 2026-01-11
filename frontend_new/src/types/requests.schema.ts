import { z } from 'zod';

export const mediaTypeSchema = z.enum(['movie', 'series']);
export type MediaType = z.infer<typeof mediaTypeSchema>;

export const mediaRequestStatusSchema = z.enum([
  'pending',
  'searching',
  'downloading',
  'completed',
  'failed',
]);
export type MediaRequestStatus = z.infer<typeof mediaRequestStatusSchema>;

export const baseRequestSchema = z.object({
  id: z.string(),
  title: z.string(),
  year: z.number().int(),
  poster_url: z.string(),
  overview: z.string(),
  genres: z.array(z.string()),
  status: mediaRequestStatusSchema,
  created_at: z.string(),
  updated_at: z.string(),
});
export type BaseRequest = z.infer<typeof baseRequestSchema>;

export const movieRequestSchema = baseRequestSchema.extend({
  type: z.literal('movie'),
  runtime: z.number().int(),
  imdb_id: z.string(),
});
export type MovieRequest = z.infer<typeof movieRequestSchema>;

export const seriesRequestSchema = baseRequestSchema.extend({
  type: z.literal('series'),
  season_number: z.number().int(),
  total_episodes: z.number().int(),
  series_title: z.string(),
  series_year: z.number().int(),
  imdb_id: z.string(),
});
export type SeriesRequest = z.infer<typeof seriesRequestSchema>;

export const mediaRequestSchema = z.discriminatedUnion('type', [
  movieRequestSchema,
  seriesRequestSchema,
]);
export type MediaRequest = z.infer<typeof mediaRequestSchema>;

export const requestsResponseSchema = z.object({
  requests: z.array(mediaRequestSchema),
  total: z.number().int().nonnegative(),
  page: z.number().int().min(1),
  per_page: z.number().int().min(1),
});
export type RequestsResponse = z.infer<typeof requestsResponseSchema>;

export const mediaRequestUpdateSchema = z.object({
  title: z.string().nullable().optional(),
  year: z.number().int().nullable().optional(),
  poster_url: z.string().nullable().optional(),
  overview: z.string().nullable().optional(),
  genres: z.array(z.string()).nullable().optional(),
  status: mediaRequestStatusSchema.optional(),
  runtime: z.number().int().nullable().optional(),
  imdb_id: z.string().nullable().optional(),
  season_number: z.number().int().nullable().optional(),
  total_episodes: z.number().int().nullable().optional(),
  series_title: z.string().nullable().optional(),
  series_year: z.number().int().nullable().optional(),
});
export type MediaRequestUpdate = z.infer<typeof mediaRequestUpdateSchema>;

export const mediaRequestCreateSchema = z.union([
  z.object({
    type: z.literal('movie'),
    title: z.string(),
    year: z.number().int(),
    runtime: z.number().int(),
    imdb_id: z.string(),
    overview: z.string().optional(),
    poster_url: z.string().optional(),
    genres: z.array(z.string()).optional(),
  }),
  z.object({
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
  }),
]);
export type MediaRequestCreate = z.infer<typeof mediaRequestCreateSchema>;

export const requestsQuerySchema = z.object({
  page: z.number().int().min(1).optional(),
  per_page: z.number().int().min(1).optional(),
  status: mediaRequestStatusSchema.optional(),
  type: mediaTypeSchema.optional(),
});
export type RequestsQuery = z.infer<typeof requestsQuerySchema>;
