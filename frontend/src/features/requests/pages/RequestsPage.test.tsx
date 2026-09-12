import { screen, waitFor } from '@testing-library/react';
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

const series: MediaRequest = {
  id: '2',
  type: 'series',
  title: 'Severance',
  year: 2022,
  season_number: 2,
  total_episodes: 10,
  series_title: 'Severance',
  series_year: 2022,
  imdb_id: 'tt11280740',
  poster_url: 'https://example.test/severance.jpg',
  overview: 'Employees undergo a memory-severing procedure.',
  genres: ['Drama'],
  status: 'downloading',
  created_at: '2026-02-01T00:00:00.000Z',
  updated_at: '2026-02-02T00:00:00.000Z',
};

describe('RequestsPage', () => {
  beforeEach(() => {
    vi.mocked(apiRequest).mockReset();
    vi.mocked(apiRequest).mockResolvedValue({ requests: [movie, series], total: 2 });
  });

  it('renders requests returned by the API', async () => {
    renderWithProviders(<RequestsPage />);

    expect(await screen.findByText('The Dark Knight')).toBeInTheDocument();
    expect(screen.getByText('Severance')).toBeInTheDocument();
  });

  it('applies the type filter from the URL', async () => {
    renderWithProviders(<RequestsPage />, { route: '/?filter=movies' });

    await waitFor(() => expect(screen.getByText('The Dark Knight')).toBeInTheDocument());
    expect(screen.queryByText('Severance')).not.toBeInTheDocument();
  });

  it('shows an empty state when the API returns no requests', async () => {
    vi.mocked(apiRequest).mockResolvedValue({ requests: [], total: 0 });

    renderWithProviders(<RequestsPage />);

    expect(await screen.findByText(/no requests/i)).toBeInTheDocument();
  });
});
