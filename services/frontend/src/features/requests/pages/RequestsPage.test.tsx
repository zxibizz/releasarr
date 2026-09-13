import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { RequestsPage } from '@/features/requests/pages/RequestsPage';
import { apiRequest } from '@/lib/api/client';
import { renderWithProviders } from '@/test/utils';
import type { MediaRequest } from '@/types';
import { formatDate } from '@/utils/formatters';

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
  exported_at: '2026-03-04T12:00:00.000Z',
};

/**
 * Built with the same formatter the card uses: the output follows the machine's
 * locale and timezone, so a hardcoded date would only pass in one of them.
 */
const exportedLabel = (value: string) => `Last exported at ${formatDate(value)}`;

/** The localized names behind the count badges, which the emoji cannot convey. */
const countLabels = (card: HTMLElement): string[] =>
  within(card)
    .queryAllByLabelText(/^(Downloaded|Pending|Unaired) \d+$/)
    .map((element) => element.getAttribute('aria-label') ?? '');

describe('RequestsPage', () => {
  beforeEach(() => {
    vi.mocked(apiRequest).mockReset();
    vi.mocked(apiRequest).mockResolvedValue({ requests: [movie, series], total: 2 });
  });

  it('renders requests returned by the API', async () => {
    renderWithProviders(<RequestsPage />, { route: '/?status=all' });

    expect(await screen.findByText('The Dark Knight')).toBeInTheDocument();
    expect(screen.getByText('Severance')).toBeInTheDocument();
  });

  it('hides requests that have already completed by default', async () => {
    renderWithProviders(<RequestsPage />);

    // `movie` is completed; `series` is still downloading.
    expect(await screen.findByText('Severance')).toBeInTheDocument();
    expect(screen.queryByText('The Dark Knight')).not.toBeInTheDocument();
  });

  it('counts a failed request as still unfinished', async () => {
    vi.mocked(apiRequest).mockResolvedValue({
      requests: [{ ...movie, id: '3', title: 'Tenet', status: 'failed' }],
      total: 1,
    });

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
    vi.mocked(apiRequest).mockResolvedValue({ requests: [], total: 0 });

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
    vi.mocked(apiRequest).mockResolvedValue({
      requests: [{ ...series, episode_counts: { downloaded: 10, pending: 0, unaired: 0 } }],
      total: 1,
    });

    renderWithProviders(<RequestsPage />);

    await screen.findByText('Severance');
    expect(screen.getByText('✅ 10')).toBeInTheDocument();
    expect(screen.queryByText('⏳ 0')).not.toBeInTheDocument();
    expect(screen.queryByText('◻️ 0')).not.toBeInTheDocument();
  });

  it('says nothing about a season the sync has not counted yet', async () => {
    // Null means "not synchronised", which must not read as "nothing downloaded".
    vi.mocked(apiRequest).mockResolvedValue({
      requests: [{ ...series, episode_counts: null }],
      total: 1,
    });

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

  it('dates a request with the last time it reached an arr', async () => {
    renderWithProviders(<RequestsPage />, { route: '/?status=all' });

    await screen.findByText('Severance');
    expect(screen.getByLabelText(exportedLabel(series.exported_at!))).toBeInTheDocument();

    // Movies carry one too: the label names no app, since each media type only
    // ever reaches the one that owns it.
    vi.mocked(apiRequest).mockResolvedValue({
      requests: [{ ...movie, exported_at: '2026-03-05T12:00:00.000Z' }],
      total: 1,
    });
    renderWithProviders(<RequestsPage />, { route: '/?status=all' });

    expect(
      await screen.findByLabelText(exportedLabel('2026-03-05T12:00:00.000Z')),
    ).toBeInTheDocument();
  });

  it('leaves the date line off a request that was never exported', async () => {
    renderWithProviders(<RequestsPage />, { route: '/?status=all' });

    const movieCard = (await screen.findByText('The Dark Knight')).closest('a');
    expect(movieCard).not.toBeNull();
    expect(within(movieCard!).queryByText(/^Last exported at /)).not.toBeInTheDocument();
  });

  it('puts the export date on the left and the counts on the right', async () => {
    renderWithProviders(<RequestsPage />, { route: '/?status=all' });

    const date = await screen.findByLabelText(exportedLabel(series.exported_at!));
    const counts = screen.getByLabelText('Downloaded 7');

    // `space-between` orders them, so document order has to be date-then-counts.
    expect(date.compareDocumentPosition(counts) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });
});
