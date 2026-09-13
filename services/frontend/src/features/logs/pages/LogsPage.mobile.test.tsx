import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { LogsPage } from '@/features/logs/pages/LogsPage';
import { apiRequest } from '@/lib/api/client';
import { DESKTOP_WIDTH, MOBILE_WIDTH, renderWithProviders, setViewportWidth } from '@/test/utils';
import type { RequestLogEntry } from '@/types';

vi.mock('@/lib/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/client')>('@/lib/api/client');
  return { ...actual, apiRequest: vi.fn() };
});

const logEntry: RequestLogEntry = {
  id: 'log-1',
  occurredAt: Date.now(),
  timestamp: 'Sep 12, 2026, 10:00:00',
  level: 'info',
  message: 'Imported a release into Sonarr',
  source: 'src.application.use_cases.releases.export_finished',
  metadata: { service: 'scheduler', task: 'release_sync' },
};

beforeEach(() => {
  vi.mocked(apiRequest).mockReset();
  vi.mocked(apiRequest).mockImplementation(async (path: string) => {
    if (path === '/logs') return { logs: [logEntry], total: 1, page: 1, per_page: 25 };
    throw new Error(`Unexpected request: ${path}`);
  });
});

afterEach(() => {
  setViewportWidth(DESKTOP_WIDTH);
});

const openSchedulerTab = async (user: ReturnType<typeof userEvent.setup>) => {
  await user.click(await screen.findByRole('tab', { name: 'Scheduler' }));
};

/** Both tab panels are mounted; `getByRole` skips the hidden one, `getByText` does not. */
const visiblePanel = () => within(screen.getByRole('tabpanel'));

describe('LogsPage on a phone', () => {
  it('keeps the tabs reachable and states each entry as a card', async () => {
    setViewportWidth(MOBILE_WIDTH);

    renderWithProviders(<LogsPage />);
    await openSchedulerTab(userEvent.setup());

    expect(await visiblePanel().findByText('Imported a release into Sonarr')).toBeInTheDocument();

    // A table here would only be reachable by scrolling horizontally.
    await waitFor(() => expect(screen.queryByRole('table')).not.toBeInTheDocument());
    expect(within(screen.getByRole('tablist')).getAllByRole('tab')).toHaveLength(2);
  });

  it('keeps log details reachable from a log card', async () => {
    setViewportWidth(MOBILE_WIDTH);
    const user = userEvent.setup();

    renderWithProviders(<LogsPage />);
    await openSchedulerTab(user);
    await user.click(await visiblePanel().findByRole('button', { name: /show log details/i }));

    expect(
      await visiblePanel().findByText('src.application.use_cases.releases.export_finished'),
    ).toBeInTheDocument();
  });

  it('renders a real table on a wide viewport', async () => {
    setViewportWidth(DESKTOP_WIDTH);
    const user = userEvent.setup();

    renderWithProviders(<LogsPage />);
    await openSchedulerTab(user);

    expect(await visiblePanel().findByRole('table')).toBeInTheDocument();
  });
});
