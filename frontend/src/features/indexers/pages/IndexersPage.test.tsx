import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { IndexerAlertBadge } from '@/features/indexers/components/IndexerAlertBadge';
import { IndexersPage } from '@/features/indexers/pages/IndexersPage';
import { ApiError, apiRequest } from '@/lib/api/client';
import { renderWithProviders } from '@/test/utils';
import type { Indexer, IndexerTestResult } from '@/types';

vi.mock('@/lib/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/client')>('@/lib/api/client');
  return { ...actual, apiRequest: vi.fn() };
});

const indexer = (overrides: Partial<Indexer> = {}): Indexer => ({
  id: 1,
  name: 'Anthelion',
  health: 'healthy',
  enabled: true,
  protocol: 'torrent',
  privacy: 'private',
  priority: 25,
  supports_search: true,
  supports_rss: true,
  indexer_urls: ['https://anthelion.example/'],
  disabled_till: null,
  most_recent_failure: null,
  initial_failure: null,
  ...overrides,
});

type Handlers = {
  indexers?: Indexer[];
  listError?: unknown;
  testResult?: IndexerTestResult;
  testAllResults?: IndexerTestResult[];
};

const respondWith = ({ indexers = [], listError, testResult, testAllResults }: Handlers) => {
  vi.mocked(apiRequest).mockImplementation(
    async (path: string, options?: { method?: string }) => {
      if (path === '/indexers') {
        if (listError) throw listError;
        return { indexers };
      }
      if (path === '/indexers/test' && options?.method === 'POST') {
        return { results: testAllResults ?? [] };
      }
      if (/^\/indexers\/\d+\/test$/.test(path) && options?.method === 'POST') {
        return testResult ?? { indexer_id: 1, name: 'Anthelion', success: true, errors: [] };
      }
      throw new Error(`Unexpected request: ${path}`);
    },
  );
};

describe('IndexersPage', () => {
  beforeEach(() => {
    vi.mocked(apiRequest).mockReset();
  });

  it('lists each indexer with its health and capabilities', async () => {
    respondWith({ indexers: [indexer()] });

    renderWithProviders(<IndexersPage />);

    const name = await screen.findByText('Anthelion');
    const row = name.closest('tr') as HTMLElement;
    expect(within(row).getByText(/Healthy/)).toBeInTheDocument();
    expect(within(row).getByText('torrent')).toBeInTheDocument();
    expect(within(row).getByText('25')).toBeInTheDocument();
    expect(within(row).getByText('Search · RSS')).toBeInTheDocument();
  });

  it('distinguishes an indexer Prowlarr blocked from one somebody switched off', async () => {
    respondWith({
      indexers: [
        indexer({
          id: 2,
          name: 'BeyondHD',
          health: 'blocked',
          disabled_till: new Date(Date.now() + 4 * 3_600_000).toISOString(),
          most_recent_failure: new Date(Date.now() - 3_600_000).toISOString(),
        }),
        indexer({ id: 3, name: 'RuTracker', health: 'disabled', enabled: false }),
      ],
    });

    renderWithProviders(<IndexersPage />);

    const blockedRow = (await screen.findByText('BeyondHD')).closest('tr') as HTMLElement;
    expect(within(blockedRow).getByText(/Blocked/)).toBeInTheDocument();

    const disabledRow = screen.getByText('RuTracker').closest('tr') as HTMLElement;
    expect(within(disabledRow).getByText(/Disabled/)).toBeInTheDocument();
  });

  it('calls out the failing indexers by name so the page answers at a glance', async () => {
    respondWith({
      indexers: [indexer(), indexer({ id: 3, name: 'Nyaa', health: 'degraded' })],
    });

    renderWithProviders(<IndexersPage />);

    expect(await screen.findByText('Some indexers need attention')).toBeInTheDocument();
    expect(screen.getByText(/Nyaa is failing/)).toBeInTheDocument();
  });

  it('tests one indexer from its row button', async () => {
    const user = userEvent.setup();
    respondWith({ indexers: [indexer({ id: 7, name: 'Nyaa', health: 'blocked' })] });

    renderWithProviders(<IndexersPage />);

    await user.click(await screen.findByRole('button', { name: /test nyaa/i }));

    await waitFor(() => {
      expect(vi.mocked(apiRequest)).toHaveBeenCalledWith(
        '/indexers/7/test',
        expect.objectContaining({ method: 'POST' }),
      );
    });
  });

  it('tests every indexer at once from the header', async () => {
    const user = userEvent.setup();
    respondWith({ indexers: [indexer()], testAllResults: [] });

    renderWithProviders(<IndexersPage />);

    await user.click(await screen.findByRole('button', { name: /test all/i }));

    await waitFor(() => {
      expect(vi.mocked(apiRequest)).toHaveBeenCalledWith(
        '/indexers/test',
        expect.objectContaining({ method: 'POST' }),
      );
    });
  });

  it('says Prowlarr is unconfigured rather than showing an empty list', async () => {
    respondWith({ listError: new ApiError('Prowlarr is not configured', { status: 503 }) });

    renderWithProviders(<IndexersPage />);

    expect(await screen.findByText('Prowlarr is not configured')).toBeInTheDocument();
    expect(screen.queryByText('No indexers yet')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /test all/i })).toBeDisabled();
  });

  it('offers a retry when Prowlarr is configured but unreachable', async () => {
    respondWith({ listError: new ApiError('Bad gateway', { status: 502 }) });

    renderWithProviders(<IndexersPage />);

    expect(await screen.findByText('Could not load indexers')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument();
  });

  it('reports an empty Prowlarr as empty', async () => {
    respondWith({ indexers: [] });

    renderWithProviders(<IndexersPage />);

    expect(await screen.findByText('No indexers yet')).toBeInTheDocument();
  });
});

describe('IndexerAlertBadge', () => {
  beforeEach(() => {
    vi.mocked(apiRequest).mockReset();
  });

  it('counts the indexers needing attention', async () => {
    respondWith({
      indexers: [
        indexer(),
        indexer({ id: 2, name: 'BeyondHD', health: 'blocked' }),
        indexer({ id: 3, name: 'Nyaa', health: 'degraded' }),
        indexer({ id: 4, name: 'RuTracker', health: 'disabled', enabled: false }),
      ],
    });

    renderWithProviders(<IndexerAlertBadge />);

    // Switched off by hand is not a problem to report; the other two are.
    expect(await screen.findByText('2')).toBeInTheDocument();
  });

  it('stays out of the way when every indexer is healthy', async () => {
    respondWith({ indexers: [indexer()] });

    renderWithProviders(<IndexerAlertBadge />);

    await waitFor(() => expect(vi.mocked(apiRequest)).toHaveBeenCalled());
    expect(screen.queryByText(/^\d+$/)).not.toBeInTheDocument();
  });

  it('shows nothing when Prowlarr is unconfigured, rather than a standing warning', async () => {
    respondWith({ listError: new ApiError('Prowlarr is not configured', { status: 503 }) });

    renderWithProviders(<IndexerAlertBadge />);

    await waitFor(() => expect(vi.mocked(apiRequest)).toHaveBeenCalled());
    expect(screen.queryByText(/^\d+$/)).not.toBeInTheDocument();
  });
});
