import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { IndexersPage } from '@/features/indexers/pages/IndexersPage';
import { apiRequest } from '@/lib/api/client';
import { DESKTOP_WIDTH, MOBILE_WIDTH, renderWithProviders, setViewportWidth } from '@/test/utils';
import type { Indexer } from '@/types';

vi.mock('@/lib/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/client')>('@/lib/api/client');
  return { ...actual, apiRequest: vi.fn() };
});

const blocked: Indexer = {
  id: 2,
  name: 'BeyondHD',
  health: 'blocked',
  enabled: true,
  protocol: 'torrent',
  privacy: 'private',
  priority: 10,
  supports_search: true,
  supports_rss: true,
  indexer_urls: ['https://beyondhd.example/'],
  disabled_till: new Date(Date.now() + 4 * 3_600_000).toISOString(),
  most_recent_failure: new Date(Date.now() - 3_600_000).toISOString(),
  initial_failure: new Date(Date.now() - 9 * 3_600_000).toISOString(),
};

beforeEach(() => {
  vi.mocked(apiRequest).mockReset();
  vi.mocked(apiRequest).mockImplementation(async (path: string) => {
    if (path === '/indexers') return { indexers: [blocked] };
    if (path === '/indexers/2/test') {
      return { indexer_id: 2, name: 'BeyondHD', success: true, errors: [] };
    }
    throw new Error(`Unexpected request: ${path}`);
  });
});

afterEach(() => {
  setViewportWidth(DESKTOP_WIDTH);
});

describe('IndexersPage on a phone', () => {
  it('states every indexer field in place of a sideways-scrolling table', async () => {
    setViewportWidth(MOBILE_WIDTH);

    renderWithProviders(<IndexersPage />);

    expect(await screen.findByText('BeyondHD')).toBeInTheDocument();

    // A table here would only be reachable by scrolling horizontally.
    await waitFor(() => expect(screen.queryByRole('table')).not.toBeInTheDocument());

    // The column headers become per-field labels, so the values stay readable.
    expect(screen.getByText('Protocol')).toBeInTheDocument();
    expect(screen.getByText('torrent · private')).toBeInTheDocument();
    expect(screen.getByText('Priority')).toBeInTheDocument();
    expect(screen.getByText('Last failure')).toBeInTheDocument();
  });

  it('keeps the health badge and test action on the card', async () => {
    setViewportWidth(MOBILE_WIDTH);
    const user = userEvent.setup();

    renderWithProviders(<IndexersPage />);

    expect(await screen.findByText('⛔ Blocked')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /test beyondhd/i }));

    await waitFor(() => {
      expect(vi.mocked(apiRequest)).toHaveBeenCalledWith(
        '/indexers/2/test',
        expect.objectContaining({ method: 'POST' }),
      );
    });
  });

  it('still renders a real table on a wide viewport', async () => {
    setViewportWidth(DESKTOP_WIDTH);

    renderWithProviders(<IndexersPage />);

    expect(await screen.findByText('BeyondHD')).toBeInTheDocument();
    await waitFor(() => expect(screen.getAllByRole('table').length).toBeGreaterThan(0));
  });
});
