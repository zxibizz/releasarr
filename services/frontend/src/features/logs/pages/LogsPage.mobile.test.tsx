import { screen, waitFor } from '@testing-library/react';
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
  component: 'usecase.export',
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

describe('LogsPage on a phone', () => {
  it('states each entry as a card with its component', async () => {
    setViewportWidth(MOBILE_WIDTH);

    renderWithProviders(<LogsPage />);

    expect(await screen.findByText('Imported a release into Sonarr')).toBeInTheDocument();
    expect(screen.getAllByText('usecase.export').length).toBeGreaterThan(0);

    // A table here would only be reachable by scrolling horizontally.
    await waitFor(() => expect(screen.queryByRole('table')).not.toBeInTheDocument());
  });

  it('keeps log details reachable from a log card', async () => {
    setViewportWidth(MOBILE_WIDTH);
    const user = userEvent.setup();

    renderWithProviders(<LogsPage />);
    await user.click(await screen.findByRole('button', { name: /show log details/i }));

    expect(
      await screen.findByText('src.application.use_cases.releases.export_finished'),
    ).toBeInTheDocument();
  });

  it('renders a real table on a wide viewport', async () => {
    setViewportWidth(DESKTOP_WIDTH);

    renderWithProviders(<LogsPage />);

    expect(await screen.findByRole('table')).toBeInTheDocument();
  });
});
