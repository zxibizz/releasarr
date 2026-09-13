import { act, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import i18n from 'i18next';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { RequestDetailPage } from '@/features/requests/pages/RequestDetailPage';
import { ApiError, apiRequest } from '@/lib/api/client';
import { renderWithProviders } from '@/test/utils';
import type { MediaRequest, SeasonEpisode, SeasonOption, SeriesSeasonsResponse } from '@/types';

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
  // No `eng` entry, so an English page falls back to the title above.
  localizations: { rus: { title: 'Разделение', overview: 'Сотрудники разделяют память.' } },
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
    downloaded: option.downloaded ?? false,
    request_id: option.request_id ?? null,
  }));

const episodes = (...items: Partial<SeasonEpisode>[]): SeasonEpisode[] =>
  items.map((item, index) => ({
    episode_number: item.episode_number ?? index + 1,
    title: item.title ?? `Episode ${index + 1}`,
    status: item.status ?? 'missing',
    // An explicit null is a date Sonarr does not have, not one left unsaid.
    air_date: item.air_date === undefined ? '2026-03-01T01:00:00Z' : item.air_date,
    file_size: item.file_size ?? null,
  }));

interface RouteStubs {
  request?: MediaRequest;
  seasons?: SeasonOption[];
  /** Left empty by default, which keeps the episode table out of the way. */
  episodes?: SeasonEpisode[];
  monitorNewSeasons?: boolean;
  seasonsError?: Error;
  episodesError?: Error;
}

/** Answers each endpoint the page hits by path, as the real client does. */
const stubRoutes = ({
  request = series,
  seasons: seasonOptions = seasons(
    { season_number: 1 },
    { season_number: 2, monitored: true, requested: true },
  ),
  episodes: episodeList = [],
  monitorNewSeasons = false,
  seasonsError,
  episodesError,
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
    if (path.endsWith('/episodes')) {
      if (episodesError) {
        return Promise.reject(episodesError);
      }
      return Promise.resolve({ season_number: 2, episodes: episodeList } as never);
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
  await userEvent.click(await screen.findByRole('button', { name: 'Manage seasons' }));
  return screen.findByRole('dialog', { name: /Seasons of Severance/ });
};

describe('RequestDetailPage', () => {
  beforeEach(() => {
    vi.mocked(apiRequest).mockReset();
    navigate.mockReset();
  });

  afterEach(async () => {
    await act(async () => {
      await i18n.changeLanguage('en');
    });
  });

  it('lists the episodes of the season with what became of each', async () => {
    stubRoutes({
      episodes: episodes(
        { title: 'Hello, Ms. Cobel', status: 'downloaded', file_size: 2 * 1024 ** 3 },
        { title: 'Goodbye, Mrs. Selvig', status: 'missing' },
        { title: 'Sweet Vitriol', status: 'unaired', air_date: null },
      ),
    });

    renderWithProviders(<RequestDetailPage />);

    const table = await screen.findByRole('table');
    const rows = within(table).getAllByRole('row').slice(1);
    expect(rows).toHaveLength(3);

    expect(within(rows[0]).getByText('Downloaded')).toBeInTheDocument();
    expect(within(rows[0]).getByText('2 GB')).toBeInTheDocument();
    expect(within(rows[1]).getByText('Pending')).toBeInTheDocument();
    expect(within(rows[2]).getByText('Not aired')).toBeInTheDocument();
    // An episode with no date must still say something in its date column.
    expect(within(rows[2]).getByText('Not scheduled')).toBeInTheDocument();

    expect(screen.getByText('1 of 3 downloaded · 2 GB on disk')).toBeInTheDocument();
  });

  it('leaves the size out of the summary when nothing is on disk yet', async () => {
    stubRoutes({ episodes: episodes({ status: 'missing' }, { status: 'missing' }) });

    renderWithProviders(<RequestDetailPage />);

    expect(await screen.findByText('0 of 2 downloaded')).toBeInTheDocument();
  });

  it('has no episode table for a movie request', async () => {
    stubRoutes({ request: movie });

    renderWithProviders(<RequestDetailPage />);

    expect(await screen.findByText('Arrival')).toBeInTheDocument();
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
    // A movie has no season, so there is nothing to ask Sonarr for either.
    expect(apiRequest).not.toHaveBeenCalledWith('/requests/req-2/episodes', expect.anything());
  });

  it('keeps quiet when the episodes cannot be listed', async () => {
    /*
     * Which is the ordinary state of a request the Sonarr sync has yet to link
     * to a series, and no reason to alarm a page whose own content is fine.
     */
    stubRoutes({ episodesError: new ApiError('nothing to list', { status: 409 }) });

    renderWithProviders(<RequestDetailPage />);

    expect(
      await screen.findByRole('heading', { name: 'Severance - Season 2' }),
    ).toBeInTheDocument();
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
    expect(screen.queryByText(/downloaded$/)).not.toBeInTheDocument();
  });

  it('sums the request up in one line, dates excluded', async () => {
    stubRoutes();

    renderWithProviders(<RequestDetailPage />);

    // The series name is left out: the heading is already saying it.
    expect(
      await screen.findByText('📺 Series · 2022 · Season 2 · 10 episodes'),
    ).toBeInTheDocument();
    expect(screen.queryByText(/Feb 1, 2026/)).not.toBeInTheDocument();
  });

  it('reads the request in the language the app is set to', async () => {
    stubRoutes();
    await act(async () => {
      await i18n.changeLanguage('ru');
    });

    renderWithProviders(<RequestDetailPage />);

    expect(await screen.findByRole('heading', { name: 'Разделение' })).toBeInTheDocument();
    // The heading has stopped saying Sonarr's own name for the series, so the
    // meta line picks it up.
    expect(screen.getByText(/· Severance ·/)).toBeInTheDocument();
  });

  it('opens the season manager from the header', async () => {
    stubRoutes();

    renderWithProviders(<RequestDetailPage />);
    const dialog = await openSeasonManager();

    // Unlike the add form, a season Sonarr monitors can be untaken here.
    const monitored = await within(dialog).findByRole('checkbox', { name: /Season 2/ });
    expect(monitored).toBeChecked();
    expect(monitored).toBeEnabled();
    expect(within(dialog).getByRole('checkbox', { name: /Season 1/ })).not.toBeChecked();
  });

  it('ticks a season Sonarr monitors even where no request exists for it', async () => {
    // Which is what a season Sonarr already holds in full looks like: nothing
    // went missing, so the sync never raised a request for it.
    stubRoutes({
      seasons: seasons(
        { season_number: 1, monitored: true },
        { season_number: 2, monitored: true, requested: true },
      ),
    });

    renderWithProviders(<RequestDetailPage />);
    const dialog = await openSeasonManager();

    expect(await within(dialog).findByRole('checkbox', { name: /Season 1/ })).toBeChecked();

    // Saving untouched must therefore leave Sonarr's monitoring as it found it.
    await userEvent.click(within(dialog).getByRole('button', { name: 'Save seasons' }));

    await waitFor(() =>
      expect(apiRequest).toHaveBeenCalledWith('/requests/req-2/seasons', {
        method: 'PUT',
        body: { season_numbers: [1, 2], monitor_new_seasons: false },
      }),
    );
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

    expect(await screen.findByText(/stop monitoring Season 2/)).toBeInTheDocument();
    expect(apiRequest).not.toHaveBeenCalledWith(
      '/requests/req-2/seasons',
      expect.objectContaining({ method: 'PUT' }),
    );

    await userEvent.click(screen.getByRole('button', { name: 'Unmonitor and save' }));

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
    expect(screen.queryByRole('button', { name: 'Manage seasons' })).not.toBeInTheDocument();

    await userEvent.click(screen.getByText('Remove Request'));

    expect(await screen.findByText(/Radarr will stop monitoring this movie/)).toBeInTheDocument();
  });
});
