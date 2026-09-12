import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { TasksPage } from '@/features/tasks/pages/TasksPage';
import { apiRequest } from '@/lib/api/client';
import { renderWithProviders } from '@/test/utils';
import type { RequestLogEntry, ScheduledTask, SyncJob } from '@/types';

vi.mock('@/lib/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/client')>('@/lib/api/client');
  return { ...actual, apiRequest: vi.fn() };
});

const scheduledTask = (overrides: Partial<ScheduledTask> = {}): ScheduledTask => ({
  kind: 'export',
  interval_seconds: 300,
  last_execution: new Date(Date.now() - 60_000).toISOString(),
  last_duration_ms: 1_500,
  last_status: 'completed',
  last_error: null,
  next_execution: new Date(Date.now() + 240_000).toISOString(),
  ...overrides,
});

const job = (overrides: Partial<SyncJob> = {}): SyncJob => ({
  id: 'job-1',
  kind: 'release_sync',
  status: 'completed',
  trigger: 'download_client',
  queued_at: new Date().toISOString(),
  started_at: new Date().toISOString(),
  finished_at: new Date().toISOString(),
  duration_ms: 2_400,
  error: null,
  result: { synced: 3, failed: 0 },
  ...overrides,
});

const logEntry = (overrides: Partial<RequestLogEntry> = {}): RequestLogEntry => ({
  id: 'log-1',
  occurredAt: Date.now(),
  timestamp: 'Sep 12, 2026, 10:00:00',
  level: 'info',
  message: 'Imported a release into Sonarr',
  source: 'src.application.use_cases.releases.export_finished',
  metadata: { task: 'export', component: 'export_finished_series' },
  ...overrides,
});

type Handlers = {
  tasks?: ScheduledTask[];
  jobs?: SyncJob[];
  logs?: RequestLogEntry[];
  logTotal?: number;
};

/** Records the query each call was made with so filters can be asserted on. */
const logRequests: Record<string, unknown>[] = [];

const respondWith = ({ tasks = [], jobs = [], logs = [], logTotal }: Handlers) => {
  vi.mocked(apiRequest).mockImplementation(
    async (path: string, options?: { method?: string; query?: Record<string, unknown> }) => {
      if (path === '/tasks/scheduled') return { tasks };
      if (path === '/tasks/jobs') return { jobs };
      if (path === '/logs') {
        logRequests.push(options?.query ?? {});
        return { logs, total: logTotal ?? logs.length, page: 1, per_page: 25 };
      }
      if (options?.method === 'POST') return { operation: 'run', status: 'queued' };
      throw new Error(`Unexpected request: ${path}`);
    },
  );
};

describe('TasksPage', () => {
  beforeEach(() => {
    vi.mocked(apiRequest).mockReset();
    logRequests.length = 0;
  });

  it('lists each scheduled task with its interval and next run', async () => {
    respondWith({ tasks: [scheduledTask({ kind: 'release_sync', interval_seconds: 30 })] });

    renderWithProviders(<TasksPage />);

    // Scoped to the row, because task names also appear in the log filter.
    const interval = await screen.findByText('30s');
    const row = interval.closest('tr') as HTMLElement;
    expect(within(row).getByText('Refresh Downloads')).toBeInTheDocument();
    expect(within(row).getByText(/in 4 minutes/i)).toBeInTheDocument();
  });

  it('queues a single task from its run button', async () => {
    const user = userEvent.setup();
    respondWith({ tasks: [scheduledTask({ kind: 'regrab' })] });

    renderWithProviders(<TasksPage />);

    await user.click(await screen.findByRole('button', { name: /run regrab outdated now/i }));

    await waitFor(() => {
      expect(vi.mocked(apiRequest)).toHaveBeenCalledWith(
        '/tasks/run/regrab',
        expect.objectContaining({ method: 'POST' }),
      );
    });
  });

  it('reveals the output of a run when its row is expanded', async () => {
    const user = userEvent.setup();
    respondWith({ jobs: [job()] });

    renderWithProviders(<TasksPage />);

    const toggle = await screen.findByRole('button', {
      name: /show details for refresh downloads/i,
    });
    await user.click(toggle);

    const output = await screen.findByText('synced');
    expect(within(output.closest('tr') as HTMLElement).getByText('3')).toBeInTheDocument();
  });

  it('surfaces the error of a failed run', async () => {
    const user = userEvent.setup();
    respondWith({
      jobs: [job({ status: 'failed', error: 'sonarr unreachable', result: null })],
    });

    renderWithProviders(<TasksPage />);

    await user.click(
      await screen.findByRole('button', { name: /show details for refresh downloads/i }),
    );

    expect(await screen.findByText('sonarr unreachable')).toBeInTheDocument();
  });

  it('warns when a queued job is never picked up', async () => {
    const stale = new Date(Date.now() - 10 * 60_000).toISOString();
    respondWith({
      jobs: [job({ status: 'queued', queued_at: stale, started_at: null, finished_at: null })],
    });

    renderWithProviders(<TasksPage />);

    expect(await screen.findByText(/nothing is picking up queued tasks/i)).toBeInTheDocument();
  });

  it('shows an empty state when nothing has been run on demand', async () => {
    respondWith({ tasks: [scheduledTask()], jobs: [] });

    renderWithProviders(<TasksPage />);

    expect(await screen.findByText(/no runs yet/i)).toBeInTheDocument();
  });

  it('lists log entries with the task that produced them', async () => {
    respondWith({ logs: [logEntry()] });

    renderWithProviders(<TasksPage />);

    expect(await screen.findByText('Imported a release into Sonarr')).toBeInTheDocument();
    // Requests every task by default, so no task filter is sent.
    expect(logRequests[0]).not.toHaveProperty('task');
  });

  it('narrows the logs to one task when the filter is used', async () => {
    const user = userEvent.setup();
    respondWith({ logs: [logEntry()] });

    renderWithProviders(<TasksPage />);

    await user.click(await screen.findByRole('combobox', { name: /filter by task/i }));
    await user.click(await screen.findByRole('option', { name: 'Refresh Downloads' }));

    await waitFor(() => {
      expect(logRequests.some((query) => query.task === 'release_sync')).toBe(true);
    });
  });

  it('reveals the source and bound context of a log entry', async () => {
    const user = userEvent.setup();
    respondWith({ logs: [logEntry()] });

    renderWithProviders(<TasksPage />);

    await user.click(await screen.findByRole('button', { name: /show log details/i }));

    expect(
      await screen.findByText('src.application.use_cases.releases.export_finished'),
    ).toBeInTheDocument();
    // The task has its own column, so it is not repeated in the context line.
    expect(await screen.findByText(/component=export_finished_series/)).toBeInTheDocument();
  });

  it('pages through the log history', async () => {
    const user = userEvent.setup();
    respondWith({ logs: [logEntry()], logTotal: 60 });

    renderWithProviders(<TasksPage />);

    expect(await screen.findByText(/page 1 of 3/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /previous/i })).toBeDisabled();

    await user.click(screen.getByRole('button', { name: /next/i }));

    await waitFor(() => {
      expect(logRequests.some((query) => query.page === 2)).toBe(true);
    });
  });
});
