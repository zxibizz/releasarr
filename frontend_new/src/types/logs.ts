import { z } from 'zod';

export const requestLogLevelSchema = z.enum(['info', 'warning', 'error']);
export type RequestLogLevel = z.infer<typeof requestLogLevelSchema>;

export const requestLogMetadataValueSchema = z.union([z.string(), z.number(), z.boolean()]);

export const requestLogMetadataSchema = z.record(requestLogMetadataValueSchema);
export type RequestLogMetadata = z.infer<typeof requestLogMetadataSchema>;

export const requestLogEntrySchema = z.object({
  id: z.string(),
  occurredAt: z.number().int(),
  timestamp: z.string(),
  level: requestLogLevelSchema,
  message: z.string(),
  source: z.string().optional(),
  metadata: requestLogMetadataSchema.optional(),
  stackTrace: z.string().optional(),
});
export type RequestLogEntry = z.infer<typeof requestLogEntrySchema>;

export const logsResponseSchema = z.object({
  logs: z.array(requestLogEntrySchema),
  total: z.number().int().nonnegative(),
  page: z.number().int().min(1),
  per_page: z.number().int().min(1),
});
export type LogsResponse = z.infer<typeof logsResponseSchema>;
