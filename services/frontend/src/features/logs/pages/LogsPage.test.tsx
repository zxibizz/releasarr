import { fireEvent, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { LogsPage } from '@/features/logs/pages/LogsPage';
import { LOGS_POLL_INTERVAL_MS } from '@/features/logs/queries';
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
  message: 'Imported a release into Sonarr',
  source: 'src.application.use_cases.releases.export_finished',
  component: 'usecase.export',
  metadata: { service: 'scheduler', task: 'export', component: 'usecase.export' },
  ...overrides,
});

/** Records the query each call was made with so filters and polling can be asserted on. */
const logRequests: Record<string, unknown>[] = [];

const respondWith = (logs: RequestLogEntry[], total = logs.length) => {
  vi.mocked(apiRequest).mockImplementation(
    async (path: string, options?: { query?: Record<string, unknown> }) => {
      if (path !== '/logs') throw new Error(`Unexpected request: ${path}`);
      logRequests.push(options?.query ?? {});
      return { logs, total, page: 1, per_page: 25 };
    },
  );
};

describe('LogsPage', () => {
  beforeEach(() => {
    vi.mocked(apiRequest).mockReset();
    logRequests.length = 0;
    window.localStorage.clear();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('shows one merged stream with no tabs and a component column', async () => {
    respondWith([logEntry()]);

    renderWithProviders(<LogsPage />);

    expect(await screen.findByText('Imported a release into Sonarr')).toBeInTheDocument();
    expect(screen.queryByRole('tablist')).not.toBeInTheDocument();
    // Component column header and the entry's component cell.
    expect(screen.getByRole('columnheader', { name: 'Component' })).toBeInTheDocument();
    expect(screen.getAllByText('usecase.export').length).toBeGreaterThan(0);
    // No service filter on the request: all processes are listed together.
    expect(logRequests[0]).not.toHaveProperty('service');
  });

  it('reveals the source and bound context of a log entry', async () => {
    const user = userEvent.setup();
    respondWith([logEntry()]);

    renderWithProviders(<LogsPage />);
    await user.click(await screen.findByRole('button', { name: /show log details/i }));

    expect(
      await screen.findByText('src.application.use_cases.releases.export_finished'),
    ).toBeInTheDocument();
    // task and service stay in the context blob; component has its own column.
    expect(await screen.findByText(/task=export/)).toBeInTheDocument();
    expect(screen.getByText(/service=scheduler/)).toBeInTheDocument();
    expect(screen.queryByText(/component=usecase\.export/)).not.toBeInTheDocument();
  });

  it('narrows the log to one process', async () => {
    const user = userEvent.setup();
    respondWith([logEntry()]);

    renderWithProviders(<LogsPage />);
    await user.click(await screen.findByRole('combobox', { name: /process/i }));
    await user.click(await screen.findByRole('option', { name: 'Scheduler' }));

    await waitFor(() => {
      expect(logRequests.some((query) => query.service === 'scheduler')).toBe(true);
    });
  });

  it('narrows the log to one component', async () => {
    const user = userEvent.setup();
    respondWith([logEntry()]);

    renderWithProviders(<LogsPage />);
    await user.click(await screen.findByRole('combobox', { name: /component/i }));
    await user.click(await screen.findByRole('option', { name: 'usecase.export' }));

    await waitFor(() => {
      expect(logRequests.some((query) => query.component === 'usecase.export')).toBe(true);
    });
  });

  it('narrows the log to a level floor', async () => {
    const user = userEvent.setup();
    respondWith([logEntry({ level: 'error' })]);

    renderWithProviders(<LogsPage />);
    await user.click(await screen.findByRole('combobox', { name: /minimum level/i }));
    await user.click(await screen.findByRole('option', { name: 'Warning' }));

    await waitFor(() => {
      expect(logRequests.some((query) => query.min_level === 'warning')).toBe(true);
    });
  });

  it('opens at the level a previous visit chose', async () => {
    window.localStorage.setItem('releasarr.logLevel', 'error');
    respondWith([logEntry({ level: 'error' })]);

    renderWithProviders(<LogsPage />);

    await waitFor(() => expect(logRequests[0]?.min_level).toBe('error'));
    expect(await screen.findByRole('combobox', { name: /minimum level/i })).toHaveValue('Error');
  });

  it('pages through the log history', async () => {
    const user = userEvent.setup();
    respondWith([logEntry()], 60);

    renderWithProviders(<LogsPage />);

    expect(await screen.findByText(/page 1 of 3/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /previous/i })).toBeDisabled();

    await user.click(screen.getByRole('button', { name: /next/i }));

    await waitFor(() => {
      expect(logRequests.some((query) => query.page === 2)).toBe(true);
    });
  });

  it('shows an empty state when nothing has been logged', async () => {
    respondWith([]);

    renderWithProviders(<LogsPage />);

    expect(await screen.findByText(/no log entries/i)).toBeInTheDocument();
  });

  it('refetches the newest page on an interval', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    respondWith([logEntry()]);

    renderWithProviders(<LogsPage />);

    await waitFor(() => expect(logRequests).toHaveLength(1));

    await vi.advanceTimersByTimeAsync(LOGS_POLL_INTERVAL_MS);

    await waitFor(() => expect(logRequests.length).toBeGreaterThan(1));
  });

  it('stops following once an older page is on screen', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    respondWith([logEntry()], 60);

    renderWithProviders(<LogsPage />);

    await waitFor(() => expect(logRequests).toHaveLength(1));

    fireEvent.click(await screen.findByRole('button', { name: /next/i }));
    await waitFor(() => expect(logRequests.some((query) => query.page === 2)).toBe(true));

    const callsAfterPaging = logRequests.length;
    await vi.advanceTimersByTimeAsync(LOGS_POLL_INTERVAL_MS);

    expect(logRequests).toHaveLength(callsAfterPaging);
  });

  it('honours the filters named in the URL', async () => {
    respondWith([logEntry()]);

    renderWithProviders(<LogsPage />, {
      route: '/system/logs?service=scheduler&component=usecase.export',
    });

    await waitFor(() => {
      const call = logRequests[0];
      expect(call).toMatchObject({ service: 'scheduler', component: 'usecase.export' });
    });
  });
});
