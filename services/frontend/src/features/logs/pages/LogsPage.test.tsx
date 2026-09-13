import { fireEvent, screen, waitFor, within } from '@testing-library/react';
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
  metadata: { service: 'scheduler', task: 'export', component: 'export_finished_series' },
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

const requestedServices = () => logRequests.map((query) => query.service);

/**
 * Both tab panels are mounted, so text queries have to be scoped to the visible
 * one. `getByRole` already skips the hidden panel, which is display: none.
 */
const visiblePanel = () => within(screen.getByRole('tabpanel'));

const openSchedulerTab = async (user: ReturnType<typeof userEvent.setup>) => {
  await user.click(await screen.findByRole('tab', { name: 'Scheduler' }));
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

  it('opens on the API process and labels both tabs', async () => {
    respondWith([logEntry({ metadata: { service: 'api' } })]);

    renderWithProviders(<LogsPage />);

    expect(await screen.findByRole('tab', { name: 'Backend' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Scheduler' })).toBeInTheDocument();
    expect(await visiblePanel().findByText('Imported a release into Sonarr')).toBeInTheDocument();
    expect(requestedServices()).toEqual(['api']);
  });

  it('asks for the other process when its tab is opened', async () => {
    const user = userEvent.setup();
    respondWith([logEntry()]);

    renderWithProviders(<LogsPage />);
    await openSchedulerTab(user);

    expect(await screen.findByRole('tab', { name: 'Scheduler' })).toHaveAttribute(
      'aria-selected',
      'true',
    );
    await waitFor(() => expect(requestedServices()).toContain('scheduler'));
    // Each tab asks for one process; nothing lists them together.
    expect(requestedServices()).not.toContain(undefined);
  });

  it('reveals the source and bound context of a log entry', async () => {
    const user = userEvent.setup();
    respondWith([logEntry()]);

    renderWithProviders(<LogsPage />);
    await openSchedulerTab(user);
    await user.click(await visiblePanel().findByRole('button', { name: /show log details/i }));

    expect(
      await visiblePanel().findByText('src.application.use_cases.releases.export_finished'),
    ).toBeInTheDocument();
    // The task has its own column and the tab carries the process.
    expect(await visiblePanel().findByText(/component=export_finished_series/)).toBeInTheDocument();
    expect(visiblePanel().queryByText(/service=/)).not.toBeInTheDocument();
  });

  it('narrows the scheduler log to one task', async () => {
    const user = userEvent.setup();
    respondWith([logEntry()]);

    renderWithProviders(<LogsPage />);
    await openSchedulerTab(user);
    await user.click(await visiblePanel().findByRole('combobox', { name: /filter by task/i }));
    await user.click(await screen.findByRole('option', { name: 'Refresh Downloads' }));

    await waitFor(() => {
      expect(logRequests.some((query) => query.task === 'release_sync')).toBe(true);
    });
  });

  it('narrows the log to a level floor', async () => {
    const user = userEvent.setup();
    respondWith([logEntry({ level: 'error' })]);

    renderWithProviders(<LogsPage />);
    await user.click(await visiblePanel().findByRole('combobox', { name: /minimum level/i }));
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
    expect(await visiblePanel().findByRole('combobox', { name: /minimum level/i })).toHaveValue(
      'Error',
    );
  });

  it('offers the level floor on both processes', async () => {
    const user = userEvent.setup();
    respondWith([logEntry()]);

    renderWithProviders(<LogsPage />);
    expect(await visiblePanel().findByRole('combobox', { name: /minimum level/i })).toBeInTheDocument();

    await openSchedulerTab(user);

    expect(await visiblePanel().findByRole('combobox', { name: /minimum level/i })).toBeInTheDocument();
  });

  it('offers no task filter for the API, which never binds a task', async () => {
    respondWith([logEntry({ metadata: { service: 'api' } })]);

    renderWithProviders(<LogsPage />);

    expect(await visiblePanel().findByText('Imported a release into Sonarr')).toBeInTheDocument();
    expect(screen.queryByRole('combobox', { name: /filter by task/i })).not.toBeInTheDocument();
  });

  it('drops a task filter when the tab changes', async () => {
    const user = userEvent.setup();
    respondWith([logEntry()]);

    renderWithProviders(<LogsPage />, { route: '/?service=scheduler' });
    await user.click(await visiblePanel().findByRole('combobox', { name: /filter by task/i }));
    await user.click(await screen.findByRole('option', { name: 'Refresh Downloads' }));
    await waitFor(() =>
      expect(logRequests.some((query) => query.task === 'release_sync')).toBe(true),
    );

    await user.click(await screen.findByRole('tab', { name: 'Backend' }));

    await waitFor(() => {
      const apiCall = logRequests.find((query) => query.service === 'api');
      // A task's records belong to the process that ran it, so carrying the
      // filter across could only ever match nothing.
      expect(apiCall).not.toHaveProperty('task');
    });
  });

  it('pages through the log history', async () => {
    const user = userEvent.setup();
    respondWith([logEntry()], 60);

    renderWithProviders(<LogsPage />);
    await openSchedulerTab(user);

    expect(await visiblePanel().findByText(/page 1 of 3/i)).toBeInTheDocument();
    expect(visiblePanel().getByRole('button', { name: /previous/i })).toBeDisabled();

    await user.click(visiblePanel().getByRole('button', { name: /next/i }));

    await waitFor(() => {
      expect(logRequests.some((query) => query.page === 2)).toBe(true);
    });
  });

  it('shows an empty state when nothing has been logged', async () => {
    respondWith([]);

    renderWithProviders(<LogsPage />);

    expect(await visiblePanel().findByText(/no log entries/i)).toBeInTheDocument();
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

    fireEvent.click(await visiblePanel().findByRole('button', { name: /next/i }));
    await waitFor(() => expect(logRequests.some((query) => query.page === 2)).toBe(true));

    const callsAfterPaging = logRequests.length;
    await vi.advanceTimersByTimeAsync(LOGS_POLL_INTERVAL_MS);

    expect(logRequests).toHaveLength(callsAfterPaging);
  });

  it('shows the process named in the URL', async () => {
    respondWith([logEntry()]);

    renderWithProviders(<LogsPage />, { route: '/system/logs?service=scheduler' });

    await waitFor(() => expect(requestedServices()).toEqual(['scheduler']));
    expect(await screen.findByRole('tab', { name: 'Scheduler' })).toHaveAttribute(
      'aria-selected',
      'true',
    );
    // The task filter belongs to the scheduler's records alone.
    expect(
      await visiblePanel().findByRole('combobox', { name: /filter by task/i }),
    ).toBeInTheDocument();
    expect(within(screen.getByRole('tablist')).getAllByRole('tab')).toHaveLength(2);
  });
});
