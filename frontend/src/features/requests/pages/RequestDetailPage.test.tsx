import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { RequestDetailPage } from '@/features/requests/pages/RequestDetailPage';
import { ApiError, apiRequest } from '@/lib/api/client';
import { renderWithProviders } from '@/test/utils';
import type { MediaRequest, SeasonOption, SeriesSeasonsResponse } from '@/types';

vi.mock('@/lib/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/client')>('@/lib/api/client');
  return { ...actual, apiRequest: vi.fn() };
});

const navigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useParams: () => ({ id: 'req-2' }),
    useNavigate: () => navigate,
  };
});

const series: MediaRequest = {
  id: 'req-2',
  type: 'series',
  title: 'Severance - Season 2',
  year: 2022,
  season_number: 2,
  total_episodes: 10,
  series_title: 'Severance',
  series_year: 2022,
  imdb_id: 'tt11280740',
  poster_url: '',
  overview: 'Employees undergo a memory-severing procedure.',
  genres: ['Drama'],
  status: 'downloading',
  created_at: '2026-02-01T00:00:00.000Z',
  updated_at: '2026-02-02T00:00:00.000Z',
};

const movie: MediaRequest = {
  id: 'req-2',
  type: 'movie',
  title: 'Arrival',
  year: 2016,
  runtime: 116,
  imdb_id: 'tt2543164',
  poster_url: '',
  overview: 'A linguist meets alien visitors.',
  genres: ['Drama'],
  status: 'completed',
  created_at: '2026-01-01T00:00:00.000Z',
  updated_at: '2026-01-02T00:00:00.000Z',
};

const seasons = (...options: Partial<SeasonOption>[]): SeasonOption[] =>
  options.map((option, index) => ({
    season_number: option.season_number ?? index + 1,
    monitored: option.monitored ?? false,
    requested: option.requested ?? false,
    request_id: option.request_id ?? null,
  }));

interface RouteStubs {
  request?: MediaRequest;
  seasons?: SeasonOption[];
  monitorNewSeasons?: boolean;
  seasonsError?: Error;
}

/** Answers each endpoint the page hits by path, as the real client does. */
const stubRoutes = ({
  request = series,
  seasons: seasonOptions = seasons({ season_number: 1 }, { season_number: 2, requested: true }),
  monitorNewSeasons = false,
  seasonsError,
}: RouteStubs = {}) => {
  const answer = (): SeriesSeasonsResponse => ({
    tvdb_id: null,
    in_library: true,
    library_id: 12,
    monitor_new_seasons: monitorNewSeasons,
    seasons: seasonOptions,
  });

  vi.mocked(apiRequest).mockImplementation((path: string, options = {}) => {
    if (path.endsWith('/seasons')) {
      if (seasonsError) {
        return Promise.reject(seasonsError);
      }
      return Promise.resolve(answer() as never);
    }
    if (path.endsWith('/releases')) {
      return Promise.resolve({ releases: [], total: 0 } as never);
    }
    if (options.method === 'DELETE') {
      return Promise.resolve(undefined as never);
    }
    return Promise.resolve(request as never);
  });
};

const openSeasonManager = async () => {
  await userEvent.click(await screen.findByRole('button', { name: /Severance \(2022\)/ }));
  return screen.findByRole('dialog', { name: /Seasons of Severance/ });
};

describe('RequestDetailPage', () => {
  beforeEach(() => {
    vi.mocked(apiRequest).mockReset();
    navigate.mockReset();
  });

  it('opens the season manager from the series name', async () => {
    stubRoutes();

    renderWithProviders(<RequestDetailPage />);
    const dialog = await openSeasonManager();

    // Unlike the add form, the season that already has a request can be untaken.
    const requested = await within(dialog).findByRole('checkbox', { name: /Season 2/ });
    expect(requested).toBeChecked();
    expect(requested).toBeEnabled();
    expect(within(dialog).getByRole('checkbox', { name: /Season 1/ })).not.toBeChecked();
  });

  it('sends a newly ticked season without asking twice', async () => {
    stubRoutes();

    renderWithProviders(<RequestDetailPage />);
    const dialog = await openSeasonManager();

    await userEvent.click(await within(dialog).findByRole('checkbox', { name: /Season 1/ }));
    await userEvent.click(within(dialog).getByRole('button', { name: 'Save seasons' }));

    await waitFor(() =>
      expect(apiRequest).toHaveBeenCalledWith('/requests/req-2/seasons', {
        method: 'PUT',
        body: { season_numbers: [2, 1], monitor_new_seasons: false },
      }),
    );
    expect(navigate).not.toHaveBeenCalled();
  });

  it('confirms before taking a season away, and leaves on removing this one', async () => {
    stubRoutes();

    renderWithProviders(<RequestDetailPage />);
    const dialog = await openSeasonManager();

    await userEvent.click(await within(dialog).findByRole('checkbox', { name: /Season 2/ }));
    await userEvent.click(within(dialog).getByRole('button', { name: 'Save seasons' }));

    expect(await screen.findByText(/Season 2.*will be removed/)).toBeInTheDocument();
    expect(apiRequest).not.toHaveBeenCalledWith(
      '/requests/req-2/seasons',
      expect.objectContaining({ method: 'PUT' }),
    );

    await userEvent.click(screen.getByRole('button', { name: 'Remove and save' }));

    await waitFor(() =>
      expect(apiRequest).toHaveBeenCalledWith('/requests/req-2/seasons', {
        method: 'PUT',
        body: { season_numbers: [], monitor_new_seasons: false },
      }),
    );
    // The season being viewed is gone, so there is no page left to stay on.
    await waitFor(() => expect(navigate).toHaveBeenCalledWith('/'));
  });

  it('says so when Sonarr has not linked the request to a series yet', async () => {
    stubRoutes({ seasonsError: new ApiError('nothing to manage', { status: 409 }) });

    renderWithProviders(<RequestDetailPage />);
    await openSeasonManager();

    expect(await screen.findByText(/has not linked this request to a series/)).toBeInTheDocument();
  });

  it('removes the request only once confirmed, then returns to the list', async () => {
    stubRoutes();

    renderWithProviders(<RequestDetailPage />);

    await userEvent.click(await screen.findByText('Remove Request'));
    expect(await screen.findByText(/Sonarr will stop monitoring this season/)).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Remove request' }));

    await waitFor(() =>
      expect(apiRequest).toHaveBeenCalledWith('/requests/req-2', { method: 'DELETE' }),
    );
    await waitFor(() => expect(navigate).toHaveBeenCalledWith('/'));
  });

  it('names Radarr when removing a movie, and offers no season manager', async () => {
    stubRoutes({ request: movie });

    renderWithProviders(<RequestDetailPage />);

    expect(await screen.findByText('Arrival')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Severance/ })).not.toBeInTheDocument();

    await userEvent.click(screen.getByText('Remove Request'));

    expect(await screen.findByText(/Radarr will stop monitoring this movie/)).toBeInTheDocument();
  });
});
