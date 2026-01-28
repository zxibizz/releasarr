import { useCallback, useMemo, useState } from 'react';

import { fetchRequestLogs } from '@/services/requestLogs';
import type { RequestLogEntry } from '@/types/logs';

type RawRequestLogEntry = Partial<RequestLogEntry> & Record<string, unknown>;

const REQUEST_LOG_LEVELS: RequestLogEntry['level'][] = ['info', 'warning', 'error'];
const MIN_TIMESTAMP_THRESHOLD = 1_000_000_000_000;

const toMilliseconds = (value: number): number => {
  return value < MIN_TIMESTAMP_THRESHOLD ? value * 1000 : value;
};

const parseNumericTimestamp = (value: unknown): number | null => {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return toMilliseconds(value);
  }

  if (typeof value === 'string' && value.trim().length > 0) {
    const numeric = Number.parseFloat(value);
    if (Number.isFinite(numeric)) {
      return toMilliseconds(numeric);
    }

    const parsedDate = Date.parse(value);
    if (!Number.isNaN(parsedDate)) {
      return parsedDate;
    }
  }

  return null;
};

const coerceMetadata = (value: unknown): Record<string, string | number | boolean> | undefined => {
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    const entries = Object.entries(value).reduce<Record<string, string | number | boolean>>(
      (acc, [key, entryValue]) => {
        if (
          typeof entryValue === 'string' ||
          typeof entryValue === 'number' ||
          typeof entryValue === 'boolean'
        ) {
          acc[key] = entryValue;
        }
        return acc;
      },
      {},
    );

    return Object.keys(entries).length > 0 ? entries : undefined;
  }

  return undefined;
};

const normalizeLogEntry = (entry: unknown, fallbackId: string): RequestLogEntry => {
  const raw: RawRequestLogEntry =
    entry && typeof entry === 'object' && !Array.isArray(entry)
      ? (entry as RawRequestLogEntry)
      : {};

  const occurredAtCandidate =
    raw.occurredAt ??
    raw.occurred_at ??
    raw.timestamp ??
    raw.time ??
    raw.createdAt ??
    raw.created_at;

  const occurredAt = parseNumericTimestamp(occurredAtCandidate) ?? Date.now();

  const idCandidate = raw.id ?? raw.logId ?? raw.log_id ?? raw.uuid ?? fallbackId;
  const id = String(idCandidate ?? fallbackId);

  const levelCandidate = (raw.level ?? raw.logLevel ?? raw.log_level ?? raw.severity) as
    | string
    | undefined;
  const normalizedLevel = levelCandidate?.toLowerCase().trim();
  const level: RequestLogEntry['level'] = REQUEST_LOG_LEVELS.includes(
    normalizedLevel as RequestLogEntry['level'],
  )
    ? (normalizedLevel as RequestLogEntry['level'])
    : 'info';

  const messageValue = raw.message ?? raw.detail ?? raw.description ?? '';
  const message = typeof messageValue === 'string' ? messageValue : String(messageValue ?? '');

  const timestampValue =
    typeof raw.timestamp === 'string'
      ? raw.timestamp
      : typeof raw.occurred_at === 'string'
        ? raw.occurred_at
        : undefined;

  const timestamp =
    (timestampValue && timestampValue.trim().length > 0
      ? timestampValue
      : new Date(occurredAt).toLocaleString()) ?? '';

  const sourceValue = raw.source ?? raw.component ?? raw.origin;
  const source = typeof sourceValue === 'string' ? sourceValue : undefined;

  const stackTraceValue = raw.stackTrace ?? raw.stack_trace ?? raw.stack;
  const stackTrace =
    typeof stackTraceValue === 'string' && stackTraceValue.trim().length > 0
      ? stackTraceValue
      : undefined;

  return {
    id,
    occurredAt,
    timestamp,
    level,
    message,
    source,
    metadata: coerceMetadata(raw.metadata ?? raw.meta ?? raw.context),
    stackTrace,
  };
};

const normalizeRequestLogs = (logs: unknown[]): RequestLogEntry[] => {
  const normalizationSeed = Date.now();
  return logs.map((log, index) => normalizeLogEntry(log, `log-${normalizationSeed}-${index}`));
};

interface UseRequestLogsState {
  logs: RequestLogEntry[];
  isLoading: boolean;
  error: string | null;
}

export const useRequestLogs = () => {
  const [state, setState] = useState<UseRequestLogsState>({
    logs: [],
    isLoading: false,
    error: null,
  });

  const loadLogs = useCallback(async (requestId: string) => {
    if (!requestId) {
      setState({ logs: [], isLoading: false, error: 'Missing request identifier' });
      return;
    }

    setState((prev) => ({ ...prev, isLoading: true, error: null }));
    try {
      const logs = await fetchRequestLogs(requestId);
      setState({ logs: normalizeRequestLogs(logs), isLoading: false, error: null });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load logs';
      setState({ logs: [], isLoading: false, error: message });
    }
  }, []);

  const reset = useCallback(() => {
    setState({ logs: [], isLoading: false, error: null });
  }, []);

  const sortedLogs = useMemo(
    () => [...state.logs].sort((a, b) => b.occurredAt - a.occurredAt),
    [state.logs],
  );

  return {
    logs: sortedLogs,
    isLoading: state.isLoading,
    error: state.error,
    loadLogs,
    reset,
  } as const;
};
