import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { RequestsPage } from '@/features/requests/pages/RequestsPage';
import { apiRequest } from '@/lib/api/client';
import { renderWithProviders } from '@/test/utils';
import type { MediaRequest } from '@/types';

vi.mock('@/lib/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/client')>('@/lib/api/client');
  return { ...actual, apiRequest: vi.fn() };
});

const movie: MediaRequest = {
  id: '1',
  type: 'movie',
  title: 'The Dark Knight',
  year: 2008,
  runtime: 152,
  imdb_id: 'tt0468569',
  poster_url: 'https://example.test/poster.jpg',
  overview: 'Batman raises the stakes in his war on crime.',
  genres: ['Action', 'Crime'],
  status: 'completed',
  created_at: '2026-01-01T00:00:00.000Z',
  updated_at: '2026-01-02T00:00:00.000Z',
};

/** Ages are counted from now, so the fixtures have to be relative to it too. */
const daysAgo = (days: number) => new Date(Date.now() - days * 86_400_000).toISOString();

const series: MediaRequest = {
  id: '2',
  type: 'series',
  title: 'Severance',
  year: 2022,
  season_number: 2,
  total_episodes: 10,
  episode_counts: { downloaded: 7, pending: 2, unaired: 1 },
  series_title: 'Severance',
  series_year: 2022,
  imdb_id: 'tt11280740',
  poster_url: 'https://example.test/severance.jpg',
  overview: 'Employees undergo a memory-severing procedure.',
  genres: ['Drama'],
  status: 'downloading',
  created_at: '2026-02-01T00:00:00.000Z',
  updated_at: '2026-02-02T00:00:00.000Z',
  newest_release_published_at: daysAgo(3),
};

const ageLabel = (age: string) => `Newest release: ${age}`;

/** The localized names behind the count badges, which the emoji cannot convey. */
const countLabels = (card: HTMLElement): string[] =>
  within(card)
    .queryAllByLabelText(/^(Downloaded|Pending|Unaired) \d+$/)
    .map((element) => element.getAttribute('aria-label') ?? '');

/** The query params the page sends; the API, not the page, applies them. */
type ListQuery = {
  query?: {
    status?: string;
    type?: string;
    has_warnings?: boolean;
    search?: string;
    page?: number;
  };
};

const mockList = (fixtures: MediaRequest[]) => {
  vi.mocked(apiRequest).mockImplementation((_path, options) => {
    const query = (options as ListQuery | undefined)?.query ?? {};
    let result = fixtures;
    if (query.status === 'active') {
      result = result.filter((request) => request.status !== 'completed');
    } else if (query.status) {
      result = result.filter((request) => request.status === query.status);
    }
    if (query.type) {
      result = result.filter((request) => request.type === query.type);
    }
    if (query.has_warnings) {
      result = result.filter((request) => (request.warnings?.length ?? 0) > 0);
    }
    if (query.search) {
      const needle = query.search.toLowerCase();
      result = result.filter((request) => request.title.toLowerCase().includes(needle));
    }
    return Promise.resolve({
      requests: result,
      total: result.length,
      page: query.page ?? 1,
      per_page: 100,
    });
  });
};

describe('RequestsPage', () => {
  beforeEach(() => {
    vi.mocked(apiRequest).mockReset();
    mockList([movie, series]);
  });

  it('renders requests returned by the API', async () => {
    renderWithProviders(<RequestsPage />, { route: '/?status=all' });

    expect(await screen.findByText('The Dark Knight')).toBeInTheDocument();
    expect(screen.getByText('Severance')).toBeInTheDocument();
  });

  it('asks the API for the active requests by default', async () => {
    renderWithProviders(<RequestsPage />);

    // `movie` is completed, so `status=active` answers without it.
    expect(await screen.findByText('Severance')).toBeInTheDocument();
    expect(screen.queryByText('The Dark Knight')).not.toBeInTheDocument();
    expect(vi.mocked(apiRequest)).toHaveBeenCalledWith(
      '/requests',
      expect.objectContaining({ query: expect.objectContaining({ status: 'active' }) }),
    );
  });

  it('counts a failed request as still unfinished', async () => {
    mockList([{ ...movie, id: '3', title: 'Tenet', status: 'failed' }]);

    renderWithProviders(<RequestsPage />);

    expect(await screen.findByText('Tenet')).toBeInTheDocument();
  });

  it('applies the type filter from the URL', async () => {
    renderWithProviders(<RequestsPage />, { route: '/?type=movie&status=all' });

    await waitFor(() => expect(screen.getByText('The Dark Knight')).toBeInTheDocument());
    expect(screen.queryByText('Severance')).not.toBeInTheDocument();
  });

  it('combines the type and status filters', async () => {
    // `movie` is completed and `series` is downloading, so asking for a
    // downloading movie has to come back empty.
    renderWithProviders(<RequestsPage />, { route: '/?type=movie&status=downloading' });

    expect(await screen.findByText(/no matching requests/i)).toBeInTheDocument();
    expect(screen.queryByText('The Dark Knight')).not.toBeInTheDocument();
    expect(screen.queryByText('Severance')).not.toBeInTheDocument();
  });

  it('keeps the status filter when the type changes', async () => {
    renderWithProviders(<RequestsPage />, { route: '/?status=downloading' });

    expect(await screen.findByText('Severance')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /^Filters/ }));
    await userEvent.click(await screen.findByRole('button', { name: 'Series' }));

    // Narrowing to series must not widen the status back to everything.
    expect(screen.getByText('Severance')).toBeInTheDocument();
    expect(screen.queryByText('The Dark Knight')).not.toBeInTheDocument();
  });

  it('keeps the filter controls behind the toggle, list first', async () => {
    renderWithProviders(<RequestsPage />, { route: '/?status=all' });

    await screen.findByText('The Dark Knight');
    expect(screen.queryByRole('button', { name: 'Movies' })).not.toBeInTheDocument();
    expect(screen.queryByRole('combobox', { name: /sort requests/i })).not.toBeInTheDocument();

    // Search is the one control that stays out in the open.
    expect(screen.getByRole('searchbox', { name: /search requests/i })).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /^Filters/ }));

    expect(await screen.findByRole('button', { name: 'Movies' })).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: /sort requests/i })).toBeInTheDocument();
  });

  it('shows an empty state when the API returns no requests', async () => {
    mockList([]);

    renderWithProviders(<RequestsPage />);

    expect(await screen.findByText(/no requests/i)).toBeInTheDocument();
  });

  it('summarises how far along a series is, and leaves movies alone', async () => {
    renderWithProviders(<RequestsPage />, { route: '/?status=all' });

    await screen.findByText('Severance');
    expect(screen.getByText('✅ 7')).toBeInTheDocument();
    expect(screen.getByText('⏳ 2')).toBeInTheDocument();
    expect(screen.getByText('◻️ 1')).toBeInTheDocument();

    // A movie has no episodes to count. Asserted on the accessible names because
    // the status badge borrows the same emoji for "completed".
    const movieCard = screen.getByText('The Dark Knight').closest('a');
    expect(movieCard).not.toBeNull();
    expect(countLabels(movieCard!)).toEqual([]);
  });

  it('leaves out the buckets that are empty rather than showing a zero', async () => {
    mockList([{ ...series, episode_counts: { downloaded: 10, pending: 0, unaired: 0 } }]);

    renderWithProviders(<RequestsPage />);

    await screen.findByText('Severance');
    expect(screen.getByText('✅ 10')).toBeInTheDocument();
    expect(screen.queryByText('⏳ 0')).not.toBeInTheDocument();
    expect(screen.queryByText('◻️ 0')).not.toBeInTheDocument();
  });

  it('says nothing about a season the sync has not counted yet', async () => {
    // Null means "not synchronised", which must not read as "nothing downloaded".
    // The generated type omits the null the contract declares, so say it here.
    mockList([{ ...series, episode_counts: null } as unknown as MediaRequest]);

    renderWithProviders(<RequestsPage />);

    const card = (await screen.findByText('Severance')).closest('a');
    expect(card).not.toBeNull();
    expect(countLabels(card!)).toEqual([]);
  });

  it('names each bucket for assistive technology, not just the emoji', async () => {
    renderWithProviders(<RequestsPage />, { route: '/?status=all' });

    await screen.findByText('Severance');
    // The emoji and the bare number are decoration; the label is the content.
    expect(screen.getByLabelText('Downloaded 7')).toBeInTheDocument();
    expect(screen.getByLabelText('Pending 2')).toBeInTheDocument();
    expect(screen.getByLabelText('Unaired 1')).toBeInTheDocument();
  });

  it('ages a request by the newest release attached to it', async () => {
    renderWithProviders(<RequestsPage />, { route: '/?status=all' });

    await screen.findByText('Severance');
    expect(screen.getByLabelText(ageLabel('3 days'))).toBeInTheDocument();

    // Anything younger than a day reads as "Today" rather than "0 days".
    mockList([{ ...movie, newest_release_published_at: daysAgo(0) }]);
    renderWithProviders(<RequestsPage />, { route: '/?status=all' });

    expect(await screen.findByLabelText(ageLabel('Today'))).toBeInTheDocument();
  });

  it('leaves the age line off a request with no dated release', async () => {
    renderWithProviders(<RequestsPage />, { route: '/?status=all' });

    const movieCard = (await screen.findByText('The Dark Knight')).closest('a');
    expect(movieCard).not.toBeNull();
    expect(within(movieCard!).queryByLabelText(/^Newest release: /)).not.toBeInTheDocument();
  });

  it('puts the release age on the left and the counts on the right', async () => {
    renderWithProviders(<RequestsPage />, { route: '/?status=all' });

    const age = await screen.findByLabelText(ageLabel('3 days'));
    const counts = screen.getByLabelText('Downloaded 7');

    // `space-between` orders them, so document order has to be age-then-counts.
    expect(age.compareDocumentPosition(counts) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('shows a warning badge only on a request that has one', async () => {
    mockList([
      {
        ...movie,
        warnings: [
          {
            code: 'regrab_indexer_unavailable',
            release_id: 'rel-1',
            details: { reason: 'indexer banned' },
            created_at: '2026-03-01T00:00:00.000Z',
          },
        ],
      },
      series,
    ]);

    renderWithProviders(<RequestsPage />, { route: '/?status=all' });

    const warnedCard = (await screen.findByText('The Dark Knight')).closest('a');
    const cleanCard = screen.getByText('Severance').closest('a');
    expect(warnedCard).not.toBeNull();
    expect(cleanCard).not.toBeNull();
    expect(within(warnedCard!).getByText('⚠️ 1')).toBeInTheDocument();
    expect(within(cleanCard!).queryByText(/⚠️/)).not.toBeInTheDocument();
  });

  it('narrows the list to problematic requests only, from the URL and the toggle', async () => {
    mockList([
      {
        ...movie,
        warnings: [
          {
            code: 'regrab_indexer_unavailable',
            release_id: 'rel-1',
            details: null,
            created_at: '2026-03-01T00:00:00.000Z',
          },
        ],
      },
      series,
    ]);

    renderWithProviders(<RequestsPage />, { route: '/?status=all&warnings=1' });

    expect(await screen.findByText('The Dark Knight')).toBeInTheDocument();
    expect(screen.queryByText('Severance')).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /^Filters/ }));
    await userEvent.click(await screen.findByRole('button', { name: /problematic only/i }));

    expect(await screen.findByText('Severance')).toBeInTheDocument();
    expect(screen.getByText('The Dark Knight')).toBeInTheDocument();
  });

  it('sends the settled search text to the API', async () => {
    // `movie` is completed, which the default active filter excludes — searching
    // within "all" is what lets it match.
    renderWithProviders(<RequestsPage />, { route: '/?status=all' });

    // The search input arrives with the list; while loading there is a skeleton.
    expect(await screen.findByText('Severance')).toBeInTheDocument();

    await userEvent.type(screen.getByRole('searchbox', { name: /search requests/i }), 'dark');

    await waitFor(() =>
      expect(vi.mocked(apiRequest)).toHaveBeenCalledWith(
        '/requests',
        expect.objectContaining({ query: expect.objectContaining({ search: 'dark' }) }),
      ),
    );
    expect(await screen.findByText('The Dark Knight')).toBeInTheDocument();
    expect(screen.queryByText('Severance')).not.toBeInTheDocument();
  });

  it('offers another page when the API says there is one', async () => {
    vi.mocked(apiRequest).mockImplementation((_path, options) => {
      const query = (options as ListQuery | undefined)?.query ?? {};
      return Promise.resolve(
        query.page === 2
          ? { requests: [series], total: 2, page: 2, per_page: 1 }
          : { requests: [movie], total: 2, page: 1, per_page: 1 },
      );
    });

    renderWithProviders(<RequestsPage />, { route: '/?status=all' });

    expect(await screen.findByText('The Dark Knight')).toBeInTheDocument();
    expect(screen.queryByText('Severance')).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /load more/i }));

    expect(await screen.findByText('Severance')).toBeInTheDocument();
    expect(screen.getByText('The Dark Knight')).toBeInTheDocument();
  });
});
