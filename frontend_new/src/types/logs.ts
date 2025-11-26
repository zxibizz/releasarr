export type RequestLogLevel = "info" | "warning" | "error";

export interface RequestLogEntry {
  id: string;
  occurredAt: number;
  timestamp: string;
  level: RequestLogLevel;
  message: string;
  source?: string;
  metadata?: Record<string, string | number | boolean>;
  stackTrace?: string;
}
