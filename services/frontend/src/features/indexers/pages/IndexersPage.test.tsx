import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { IndexerAlertBadge } from '@/features/indexers/components/IndexerAlertBadge';
import { IndexersPage } from '@/features/indexers/pages/IndexersPage';
import { ApiError, apiRequest } from '@/lib/api/client';
import { renderWithProviders } from '@/test/utils';
import type { Indexer, IndexerHistoryEntry, IndexerTestResult } from '@/types';

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

const event = (overrides: Partial<IndexerHistoryEntry> = {}): IndexerHistoryEntry => ({
  id: 412,
  indexer_id: 1,
  indexer_name: 'Anthelion',
  occurred_at: new Date(Date.now() - 5 * 60_000).toISOString(),
  event_type: 'indexer_query',
  successful: true,
  query: 'Severance S02',
  title: null,
  source: 'Sonarr',
  elapsed_ms: 412,
  data: { queryResults: '39' },
  ...overrides,
});

type Handlers = {
  indexers?: Indexer[];
  listError?: unknown;
  testResult?: IndexerTestResult;
  testAllResults?: IndexerTestResult[];
  history?: IndexerHistoryEntry[];
  historyTotal?: number;
  historyError?: unknown;
};

const respondWith = ({
  indexers = [],
  listError,
  testResult,
  testAllResults,
  history = [],
  historyTotal,
  historyError,
}: Handlers) => {
  vi.mocked(apiRequest).mockImplementation(
    async (path: string, options?: { method?: string; query?: Record<string, unknown> }) => {
      if (path === '/indexers') {
        if (listError) throw listError;
        return { indexers };
      }
      if (path === '/indexers/history') {
        if (historyError) throw historyError;
        return {
          history,
          total: historyTotal ?? history.length,
          page: Number(options?.query?.page ?? 1),
          per_page: Number(options?.query?.per_page ?? 25),
        };
      }
      // The modal opens on its Events tab, so this answers while the test moves
      // across to History rather than tripping the unexpected-request guard.
      if (path === '/indexers/logs') {
        return { logs: [], total: 0, page: 1, per_page: 25 };
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

const historyCalls = () =>
  vi.mocked(apiRequest).mock.calls.filter(([path]) => path === '/indexers/history');

/** The modal opens on Events, so history tests have to move the tab across. */
const openLogs = async (user: ReturnType<typeof userEvent.setup>) => {
  await user.click(await screen.findByRole('button', { name: /^logs$/i }));
  await user.click(await screen.findByRole('tab', { name: /^history$/i }));
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
    expect(screen.getByRole('button', { name: /^logs$/i })).toBeDisabled();
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

describe('IndexerLogsModal (history tab)', () => {
  beforeEach(() => {
    vi.mocked(apiRequest).mockReset();
  });

  it('leaves Prowlarr alone until the reader asks for the logs', async () => {
    const user = userEvent.setup();
    respondWith({ indexers: [indexer()], history: [event()] });

    renderWithProviders(<IndexersPage />);

    await screen.findByText('Anthelion');
    expect(historyCalls()).toHaveLength(0);

    await openLogs(user);

    await waitFor(() => expect(historyCalls()).toHaveLength(1));
  });

  it('shows what each event was, and what it was for', async () => {
    const user = userEvent.setup();
    respondWith({
      indexers: [indexer()],
      history: [
        event(),
        event({
          id: 411,
          event_type: 'release_grabbed',
          query: null,
          title: 'Severance.S02E01.2160p',
        }),
      ],
    });

    renderWithProviders(<IndexersPage />);
    await openLogs(user);

    // Two things make a bare query ambiguous: the page's own indexer table is
    // also a table, and the filter selects render option labels with the same
    // words in them. Narrow to the modal's table, which is what this asserts.
    const table = within(within(await screen.findByRole('dialog')).getByRole('table'));
    expect(table.getByText('Severance S02')).toBeInTheDocument();
    expect(table.getByText('Search')).toBeInTheDocument();
    expect(table.getByText('Severance.S02E01.2160p')).toBeInTheDocument();
    expect(table.getByText('Grabbed')).toBeInTheDocument();
  });

  it('keeps the noisier Prowlarr fields behind the row toggle', async () => {
    const user = userEvent.setup();
    respondWith({ indexers: [indexer()], history: [event()] });

    renderWithProviders(<IndexersPage />);
    await openLogs(user);

    await screen.findByText('Severance S02');
    // Collapse keeps its children mounted so it has something to animate, so what
    // the toggle changes is visibility rather than presence.
    const toggle = screen.getByRole('button', { name: /show event details/i });
    expect(screen.getByText(/queryResults=39/)).not.toBeVisible();

    await user.click(toggle);
    await waitFor(() => expect(toggle).toHaveAttribute('aria-expanded', 'true'));

    // The reveal is a Mantine transition, so the frame it needs can land after the
    // default second when the whole suite is running in parallel.
    await waitFor(() => expect(screen.getByText(/queryResults=39/)).toBeVisible(), {
      timeout: 3000,
    });
    expect(screen.getByText(/Asked by: Sonarr/)).toBeVisible();
    expect(screen.getByText(/Took: 412ms/)).toBeVisible();
  });

  it('narrows the history to one event type, from the first page', async () => {
    const user = userEvent.setup();
    respondWith({ indexers: [indexer()], history: [event()], historyTotal: 60 });

    renderWithProviders(<IndexersPage />);
    await openLogs(user);

    await screen.findByText('Severance S02');
    await user.click(screen.getByRole('button', { name: /next/i }));
    await waitFor(() => expect(screen.getByText(/Page 2 of 3/)).toBeInTheDocument());

    await user.click(screen.getByRole('combobox', { name: /filter by event/i }));
    await user.click(await screen.findByRole('option', { name: 'Grabbed' }));

    await waitFor(() => {
      expect(vi.mocked(apiRequest)).toHaveBeenCalledWith(
        '/indexers/history',
        expect.objectContaining({
          query: expect.objectContaining({ event_type: 'release_grabbed', page: 1 }),
        }),
      );
    });
  });

  it('narrows the history to one indexer', async () => {
    const user = userEvent.setup();
    respondWith({
      indexers: [indexer(), indexer({ id: 3, name: 'Nyaa' })],
      history: [event()],
    });

    renderWithProviders(<IndexersPage />);
    await openLogs(user);

    await screen.findByText('Severance S02');
    await user.click(screen.getByRole('combobox', { name: /filter by indexer/i }));
    await user.click(await screen.findByRole('option', { name: 'Nyaa' }));

    await waitFor(() => {
      expect(vi.mocked(apiRequest)).toHaveBeenCalledWith(
        '/indexers/history',
        expect.objectContaining({ query: expect.objectContaining({ indexer_id: 3 }) }),
      );
    });
  });

  it('reports an unreachable Prowlarr with a retry rather than an empty history', async () => {
    const user = userEvent.setup();
    respondWith({
      indexers: [indexer()],
      historyError: new ApiError('Bad gateway', { status: 502 }),
    });

    renderWithProviders(<IndexersPage />);
    await openLogs(user);

    expect(await screen.findByText('Could not load indexer logs')).toBeInTheDocument();
    expect(screen.queryByText('No events yet')).not.toBeInTheDocument();
  });

  it('says nothing matched when the filters exclude everything', async () => {
    const user = userEvent.setup();
    respondWith({ indexers: [indexer(), indexer({ id: 3, name: 'Nyaa' })], history: [] });

    renderWithProviders(<IndexersPage />);
    await openLogs(user);

    expect(await screen.findByText('No events yet')).toBeInTheDocument();
    expect(
      screen.getByText('Events appear here once something searches through Prowlarr.'),
    ).toBeInTheDocument();

    await user.click(screen.getByRole('combobox', { name: /filter by indexer/i }));
    await user.click(await screen.findByRole('option', { name: 'Nyaa' }));

    expect(await screen.findByText('Nothing matches these filters.')).toBeInTheDocument();
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
