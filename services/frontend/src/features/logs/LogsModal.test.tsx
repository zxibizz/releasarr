import { screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { LogsModal } from '@/features/logs/LogsModal';
import { apiRequest } from '@/lib/api/client';
import { renderWithProviders } from '@/test/utils';
import type { RequestLogEntry } from '@/types';

vi.mock('@/lib/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/client')>('@/lib/api/client');
  return { ...actual, apiRequest: vi.fn() };
});

const logEntry = (overrides: Partial<RequestLogEntry> = {}): RequestLogEntry => ({
  id: 'log-1',
  occurredAt: Date.now(),
  timestamp: 'Sep 12, 2026, 10:00:00',
  level: 'info',
  message: 'Grabbed release',
  component: 'usecase.queue_download',
  metadata: { request_id: 'req-1', release_name: 'Some.Show.S01E05.1080p' },
  ...overrides,
});

const capturedQueries: Record<string, unknown>[] = [];

beforeEach(() => {
  capturedQueries.length = 0;
  vi.mocked(apiRequest).mockReset();
  vi.mocked(apiRequest).mockImplementation(
    async (path: string, options?: { query?: Record<string, unknown> }) => {
      if (path !== '/logs') throw new Error(`Unexpected request: ${path}`);
      capturedQueries.push(options?.query ?? {});
      return { logs: [logEntry()], total: 1, page: 1, per_page: 100 };
    },
  );
});

describe('LogsModal', () => {
  it('asks the API for only this request’s logs while open', async () => {
    renderWithProviders(
      <LogsModal requestId="req-1" requestTitle="Some Show" opened onClose={() => {}} />,
    );

    expect(await screen.findByText('Grabbed release')).toBeInTheDocument();
    await waitFor(() => {
      expect(capturedQueries[0]).toMatchObject({ request_id: 'req-1' });
    });
    // The entry's component is shown, and the request it is scoped to is not
    // repeated in the context line.
    expect(screen.getAllByText('usecase.queue_download').length).toBeGreaterThan(0);
    expect(screen.queryByText(/request_id=req-1/)).not.toBeInTheDocument();
  });

  it('does not query until opened', () => {
    renderWithProviders(
      <LogsModal requestId="req-1" requestTitle="Some Show" opened={false} onClose={() => {}} />,
    );

    expect(capturedQueries).toHaveLength(0);
  });
});
