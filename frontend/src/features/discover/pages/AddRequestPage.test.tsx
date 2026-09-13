import { act, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { AddRequestPage } from '@/features/discover/pages/AddRequestPage';
import { apiRequest } from '@/lib/api/client';
import i18n from '@/lib/i18n';
import { renderWithProviders } from '@/test/utils';
import type { MediaSearchResult, RootFolder, SeasonOption } from '@/types';

vi.mock('@/lib/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/client')>('@/lib/api/client');
  return { ...actual, apiRequest: vi.fn() };
});

const seriesResult: MediaSearchResult = {
  type: 'series',
  provider_id: 121361,
  title: 'Game of Thrones',
  year: 2011,
  overview: 'Noble families fight for control.',
  poster_url: null,
  in_library: false,
  library_id: null,
  requested_seasons: [],
  request_id: null,
  request_status: null,
};

const knownSeries: MediaSearchResult = {
  ...seriesResult,
  provider_id: 371980,
  title: 'Severance',
  year: 2022,
  in_library: true,
  library_id: 12,
  requested_seasons: [1],
};

const movieResult: MediaSearchResult = {
  type: 'movie',
  provider_id: 329865,
  title: 'Arrival',
  year: 2016,
  overview: 'A linguist meets alien visitors.',
  poster_url: null,
  in_library: false,
  library_id: null,
  requested_seasons: [],
  request_id: null,
  request_status: null,
};

const FOLDERS: Record<'series' | 'movie', RootFolder[]> = {
  series: [
    { path: '/media/tv', free_space: 1024 ** 4 },
    { path: '/media/tv-4k', free_space: 512 * 1024 ** 3 },
  ],
  movie: [{ path: '/media/movies', free_space: 1024 ** 4 }],
};

const seasons = (...options: Partial<SeasonOption>[]): SeasonOption[] =>
  options.map((option, index) => ({
    season_number: option.season_number ?? index + 1,
    monitored: option.monitored ?? false,
    requested: option.requested ?? false,
    request_id: option.request_id ?? null,
  }));

interface RouteStubs {
  results?: MediaSearchResult[];
  /** Results to answer with per requested language, for localized searches. */
  resultsByLanguage?: Record<string, MediaSearchResult[]>;
  folders?: RootFolder[];
  seasons?: SeasonOption[];
  inLibrary?: boolean;
  monitorNewSeasons?: boolean;
  searchError?: Error;
}

/** Answers each discover endpoint by path, the way the real client hits them. */
const stubRoutes = ({
  results = [],
  resultsByLanguage,
  folders,
  seasons: seasonOptions = [],
  inLibrary = false,
  monitorNewSeasons = false,
  searchError,
}: RouteStubs) => {
  vi.mocked(apiRequest).mockImplementation((path: string, options = {}) => {
    if (path === '/discover/search') {
      if (searchError) {
        return Promise.reject(searchError);
      }
      const language = String(options.query?.lang ?? '');
      return Promise.resolve({
        results: resultsByLanguage?.[language] ?? results,
      } as never);
    }
    if (path === '/discover/root-folders') {
      // Sonarr and Radarr have separate libraries, so the type decides the paths.
      const type = options.query?.type === 'movie' ? 'movie' : 'series';
      return Promise.resolve({ folders: folders ?? FOLDERS[type] } as never);
    }
    if (path.endsWith('/seasons')) {
      return Promise.resolve({
        tvdb_id: 1,
        in_library: inLibrary,
        library_id: inLibrary ? 12 : null,
        monitor_new_seasons: monitorNewSeasons,
        seasons: seasonOptions,
      } as never);
    }
    if (path === '/discover/requests') {
      return Promise.resolve({ requests: [] } as never);
    }
    throw new Error(`unexpected path ${path}`);
  });
};

const search = async (term = 'thrones') => {
  await userEvent.type(screen.getByRole('searchbox'), term);
  await userEvent.click(screen.getByRole('button', { name: 'Search' }));
};

describe('AddRequestPage', () => {
  beforeEach(() => {
    vi.mocked(apiRequest).mockReset();
  });

  afterEach(async () => {
    await act(async () => {
      await i18n.changeLanguage('en');
    });
  });

  it('searches only on submit, so a partial term never reaches the provider', async () => {
    stubRoutes({ results: [seriesResult] });

    renderWithProviders(<AddRequestPage />);

    await userEvent.type(screen.getByRole('searchbox'), 'thro');
    expect(apiRequest).not.toHaveBeenCalled();

    await userEvent.click(screen.getByRole('button', { name: 'Search' }));

    expect(await screen.findByText('Game of Thrones')).toBeInTheDocument();
    // No type: not knowing whether a title is a movie or a series is the point.
    expect(apiRequest).toHaveBeenCalledWith(
      '/discover/search',
      expect.objectContaining({ query: { q: 'thro', lang: 'en' } }),
    );
  });

  it('searches movies and series together, labelling which each result is', async () => {
    stubRoutes({ results: [seriesResult, movieResult] });

    renderWithProviders(<AddRequestPage />);
    await search();

    expect(await screen.findByText('Game of Thrones')).toBeInTheDocument();
    expect(screen.getByText('Arrival')).toBeInTheDocument();
    expect(screen.getByText(/📺 Series/)).toBeInTheDocument();
    expect(screen.getByText(/🎬 Movie/)).toBeInTheDocument();
  });

  it('offers no way to search one kind on its own', async () => {
    stubRoutes({ results: [seriesResult, movieResult] });

    renderWithProviders(<AddRequestPage />);
    await search();

    expect(await screen.findByText('Game of Thrones')).toBeInTheDocument();
    expect(screen.queryByRole('radio', { name: 'Movie' })).not.toBeInTheDocument();
    expect(screen.queryByRole('radio', { name: 'Series' })).not.toBeInTheDocument();
  });

  it('asks the provider for the language the UI is in', async () => {
    stubRoutes({
      resultsByLanguage: {
        en: [seriesResult],
        ru: [{ ...seriesResult, title: 'Игра престолов' }],
      },
    });

    renderWithProviders(<AddRequestPage />);
    await search();

    expect(await screen.findByText('Game of Thrones')).toBeInTheDocument();

    await act(async () => {
      await i18n.changeLanguage('ru');
    });

    expect(await screen.findByText('Игра престолов')).toBeInTheDocument();
    expect(apiRequest).toHaveBeenCalledWith(
      '/discover/search',
      expect.objectContaining({ query: { q: 'thrones', lang: 'ru' } }),
    );
  });

  it('marks results Sonarr already holds and the seasons already requested', async () => {
    stubRoutes({ results: [seriesResult, knownSeries] });

    renderWithProviders(<AddRequestPage />);
    await search();

    expect(await screen.findByText('Severance')).toBeInTheDocument();
    expect(screen.getByText('In library')).toBeInTheDocument();
    expect(screen.getByText('Requested: Season 1')).toBeInTheDocument();
  });

  it('locks the seasons that already have a request', async () => {
    stubRoutes({
      results: [knownSeries],
      inLibrary: true,
      seasons: seasons(
        { season_number: 1, requested: true, request_id: 'req-1' },
        { season_number: 2 },
      ),
    });

    renderWithProviders(<AddRequestPage />);
    await search();

    await userEvent.click(await screen.findByRole('button', { name: 'Choose seasons' }));

    const requested = await screen.findByRole('checkbox', { name: /Season 1/ });
    expect(requested).toBeChecked();
    expect(requested).toBeDisabled();

    const available = screen.getByRole('checkbox', { name: /Season 2/ });
    expect(available).not.toBeChecked();
    expect(available).toBeEnabled();
  });

  it('shows a season Sonarr monitors as taken even without a request of ours', async () => {
    /*
     * A monitored season that is already complete never goes missing, so it
     * never becomes a request. Reading that as "not monitored" contradicted
     * both Sonarr and our own manage-seasons modal.
     */
    stubRoutes({
      results: [knownSeries],
      inLibrary: true,
      seasons: seasons(
        { season_number: 1, monitored: true },
        { season_number: 2, monitored: false },
      ),
    });

    renderWithProviders(<AddRequestPage />);
    await search();

    await userEvent.click(await screen.findByRole('button', { name: 'Choose seasons' }));

    const monitored = await screen.findByRole('checkbox', { name: /Season 1/ });
    expect(monitored).toBeChecked();
    expect(monitored).toBeDisabled();
    expect(screen.getByText('Already monitored in Sonarr')).toBeInTheDocument();

    const available = screen.getByRole('checkbox', { name: /Season 2/ });
    expect(available).not.toBeChecked();
    expect(available).toBeEnabled();
  });

  it('asks only for the seasons Sonarr does not already monitor', async () => {
    stubRoutes({
      results: [knownSeries],
      inLibrary: true,
      seasons: seasons(
        { season_number: 1, monitored: true },
        { season_number: 2 },
        { season_number: 3 },
      ),
    });

    renderWithProviders(<AddRequestPage />);
    await search();

    await userEvent.click(await screen.findByRole('button', { name: 'Choose seasons' }));
    await userEvent.click(await screen.findByRole('button', { name: 'Select all' }));
    await userEvent.click(screen.getByRole('button', { name: 'Add request' }));

    await waitFor(() =>
      expect(apiRequest).toHaveBeenCalledWith(
        '/discover/requests',
        expect.objectContaining({
          body: expect.objectContaining({ season_numbers: [2, 3] }),
        }),
      ),
    );
  });

  it('has nothing to add for a series Sonarr already covers entirely', async () => {
    stubRoutes({
      results: [knownSeries],
      inLibrary: true,
      seasons: seasons(
        { season_number: 1, monitored: true },
        { season_number: 2, monitored: true },
      ),
    });

    renderWithProviders(<AddRequestPage />);
    await search();

    await userEvent.click(await screen.findByRole('button', { name: 'Choose seasons' }));

    expect(
      await screen.findByText('Sonarr already covers every season of this series.'),
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Add request' })).toBeDisabled();
  });

  it('asks Sonarr for future seasons when the box is ticked', async () => {
    stubRoutes({
      results: [seriesResult],
      seasons: seasons({ season_number: 1 }),
    });

    renderWithProviders(<AddRequestPage />);
    await search();

    await userEvent.click(await screen.findByRole('button', { name: 'Choose seasons' }));
    await userEvent.click(await screen.findByRole('checkbox', { name: /Season 1/ }));
    await userEvent.click(screen.getByRole('checkbox', { name: /New seasons/ }));
    await userEvent.click(screen.getByRole('button', { name: 'Add request' }));

    await waitFor(() =>
      expect(apiRequest).toHaveBeenCalledWith(
        '/discover/requests',
        expect.objectContaining({
          body: expect.objectContaining({ monitor_new_seasons: true }),
        }),
      ),
    );
  });

  it('keeps the future seasons a library series is already set to take', async () => {
    /* Starting the box unticked would switch them off as a side effect. */
    stubRoutes({
      results: [knownSeries],
      inLibrary: true,
      monitorNewSeasons: true,
      seasons: seasons({ season_number: 1 }, { season_number: 2 }),
    });

    renderWithProviders(<AddRequestPage />);
    await search();

    await userEvent.click(await screen.findByRole('button', { name: 'Choose seasons' }));

    expect(await screen.findByRole('checkbox', { name: /New seasons/ })).toBeChecked();
  });

  it('will not submit a series until a season is picked', async () => {
    stubRoutes({
      results: [seriesResult],
      seasons: seasons({ season_number: 1 }, { season_number: 2 }),
    });

    renderWithProviders(<AddRequestPage />);
    await search();

    await userEvent.click(await screen.findByRole('button', { name: 'Choose seasons' }));

    const confirm = await screen.findByRole('button', { name: 'Add request' });
    expect(confirm).toBeDisabled();

    await userEvent.click(screen.getByRole('checkbox', { name: /Season 2/ }));

    expect(confirm).toBeEnabled();
  });

  it('sends the picked seasons and folder, and nothing else', async () => {
    stubRoutes({
      results: [seriesResult],
      seasons: seasons({ season_number: 1 }, { season_number: 2 }, { season_number: 3 }),
    });

    renderWithProviders(<AddRequestPage />);
    await search();

    await userEvent.click(await screen.findByRole('button', { name: 'Choose seasons' }));
    await userEvent.click(await screen.findByRole('checkbox', { name: /Season 1/ }));
    await userEvent.click(screen.getByRole('checkbox', { name: /Season 3/ }));
    await userEvent.click(screen.getByRole('button', { name: 'Add request' }));

    await waitFor(() =>
      expect(apiRequest).toHaveBeenCalledWith('/discover/requests', {
        method: 'POST',
        body: {
          type: 'series',
          provider_id: 121361,
          // The first folder is offered as the default, so it needs no click.
          root_folder_path: '/media/tv',
          season_numbers: [1, 3],
          monitor_new_seasons: false,
        },
      }),
    );
  });

  it('adds every season at once when asked to', async () => {
    stubRoutes({
      results: [seriesResult],
      seasons: seasons({ season_number: 1 }, { season_number: 2 }, { season_number: 3 }),
    });

    renderWithProviders(<AddRequestPage />);
    await search();

    await userEvent.click(await screen.findByRole('button', { name: 'Choose seasons' }));
    await userEvent.click(await screen.findByRole('button', { name: 'Select all' }));
    await userEvent.click(screen.getByRole('button', { name: 'Add request' }));

    await waitFor(() =>
      expect(apiRequest).toHaveBeenCalledWith(
        '/discover/requests',
        expect.objectContaining({
          body: expect.objectContaining({ season_numbers: [1, 2, 3] }),
        }),
      ),
    );
  });

  it('does not offer the specials, which are rarely what a request means', async () => {
    stubRoutes({
      results: [seriesResult],
      seasons: seasons({ season_number: 0 }, { season_number: 1 }),
    });

    renderWithProviders(<AddRequestPage />);
    await search();

    await userEvent.click(await screen.findByRole('button', { name: 'Choose seasons' }));

    expect(await screen.findByRole('checkbox', { name: /Season 1/ })).toBeInTheDocument();
    expect(screen.queryByRole('checkbox', { name: /Specials/ })).not.toBeInTheDocument();
  });

  it('lays the seasons out down each column, so they read in order', async () => {
    stubRoutes({
      results: [seriesResult],
      seasons: seasons(
        { season_number: 1 },
        { season_number: 2 },
        { season_number: 3 },
        { season_number: 4 },
        { season_number: 5 },
      ),
    });

    renderWithProviders(<AddRequestPage />);
    await search();

    await userEvent.click(await screen.findByRole('button', { name: 'Choose seasons' }));

    const first = await screen.findByRole('checkbox', { name: /Season 1/ });
    // Three columns of two rows, filled downwards: 1-2, 3-4, 5.
    const grid = first.closest('[style*="grid-auto-flow"]');
    expect(grid).toHaveStyle({ gridAutoFlow: 'column', gridTemplateRows: 'repeat(2, auto)' });
  });

  it('asks a movie for nothing but the folder', async () => {
    stubRoutes({ results: [movieResult] });

    renderWithProviders(<AddRequestPage />);
    await search('arrival');

    await userEvent.click(await screen.findByRole('button', { name: 'Request' }));

    expect(screen.queryByText('Seasons')).not.toBeInTheDocument();
    await userEvent.click(await screen.findByRole('button', { name: 'Add request' }));

    await waitFor(() =>
      expect(apiRequest).toHaveBeenCalledWith('/discover/requests', {
        method: 'POST',
        body: {
          type: 'movie',
          provider_id: 329865,
          root_folder_path: '/media/movies',
          season_numbers: undefined,
          monitor_new_seasons: false,
        },
      }),
    );
  });

  it('hides the folder picker for media the *arr app already holds', async () => {
    stubRoutes({
      results: [knownSeries],
      inLibrary: true,
      seasons: seasons({ season_number: 1 }),
    });

    renderWithProviders(<AddRequestPage />);
    await search();

    await userEvent.click(await screen.findByRole('button', { name: 'Choose seasons' }));

    expect(await screen.findByText(/already in Sonarr/i)).toBeInTheDocument();
    expect(screen.queryByRole('textbox', { name: 'Library folder' })).not.toBeInTheDocument();
  });

  it('reports a failed search without losing the term', async () => {
    stubRoutes({ searchError: new Error('TVDB is unreachable') });

    renderWithProviders(<AddRequestPage />);
    await search();

    expect(await screen.findByText('Search failed')).toBeInTheDocument();
    expect(screen.getByText('TVDB is unreachable')).toBeInTheDocument();
    expect(screen.getByRole('searchbox')).toHaveValue('thrones');
  });

  it('shows an empty state when the provider has no match', async () => {
    stubRoutes({ results: [] });

    renderWithProviders(<AddRequestPage />);
    await search('nothing at all');

    expect(await screen.findByText('No matches found')).toBeInTheDocument();
  });

  it('prompts for a search before anything has been typed', () => {
    stubRoutes({});

    renderWithProviders(<AddRequestPage />);

    expect(screen.getByText('Search for something to request')).toBeInTheDocument();
    expect(apiRequest).not.toHaveBeenCalled();
  });
});
