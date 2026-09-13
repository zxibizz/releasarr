import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { TasksPage } from '@/features/tasks/pages/TasksPage';
import { apiRequest } from '@/lib/api/client';
import { DESKTOP_WIDTH, MOBILE_WIDTH, renderWithProviders, setViewportWidth } from '@/test/utils';
import type { ScheduledTask, SyncJob } from '@/types';

vi.mock('@/lib/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/client')>('@/lib/api/client');
  return { ...actual, apiRequest: vi.fn() };
});

const task: ScheduledTask = {
  kind: 'release_sync',
  interval_seconds: 30,
  last_execution: new Date(Date.now() - 60_000).toISOString(),
  last_duration_ms: 1_500,
  last_status: 'completed',
  last_error: null,
  next_execution: new Date(Date.now() + 240_000).toISOString(),
};

const job: SyncJob = {
  id: 'job-1',
  kind: 'release_sync',
  status: 'completed',
  trigger: 'download_client',
  queued_at: new Date().toISOString(),
  started_at: new Date().toISOString(),
  finished_at: new Date().toISOString(),
  duration_ms: 2_400,
  error: null,
  result: { synced: 3 },
};

beforeEach(() => {
  vi.mocked(apiRequest).mockReset();
  vi.mocked(apiRequest).mockImplementation(async (path: string) => {
    if (path === '/tasks/scheduled') return { tasks: [task] };
    if (path === '/tasks/jobs') return { jobs: [job] };
    throw new Error(`Unexpected request: ${path}`);
  });
});

afterEach(() => {
  setViewportWidth(DESKTOP_WIDTH);
});

describe('TasksPage on a phone', () => {
  it('states every task field in place of a sideways-scrolling table', async () => {
    setViewportWidth(MOBILE_WIDTH);

    renderWithProviders(<TasksPage />);

    // Scoped to the section, because the same task is also listed in the queue.
    const scheduled = (await screen.findByText('Scheduled')).closest('div') as HTMLElement;
    expect(await within(scheduled).findByText('Refresh Downloads')).toBeInTheDocument();

    // A table here would only be reachable by scrolling horizontally.
    await waitFor(() => expect(screen.queryByRole('table')).not.toBeInTheDocument());

    // The column headers become per-field labels, so the values stay readable.
    expect(within(scheduled).getByText('Interval')).toBeInTheDocument();
    expect(within(scheduled).getByText('30s')).toBeInTheDocument();
    expect(within(scheduled).getByText('Last duration')).toBeInTheDocument();
  });

  it('keeps run output reachable from a queue card', async () => {
    setViewportWidth(MOBILE_WIDTH);
    const user = userEvent.setup();

    renderWithProviders(<TasksPage />);

    await user.click(
      await screen.findByRole('button', { name: /show details for refresh downloads/i }),
    );

    expect(await screen.findByText('synced')).toBeInTheDocument();
  });

  it('still renders real tables on a wide viewport', async () => {
    setViewportWidth(DESKTOP_WIDTH);

    renderWithProviders(<TasksPage />);

    await waitFor(() => expect(screen.getAllByRole('table').length).toBeGreaterThan(0));
  });
});
