import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { AddRequestPage } from '@/features/discover/pages/AddRequestPage';
import { apiRequest } from '@/lib/api/client';
import { DESKTOP_WIDTH, MOBILE_WIDTH, renderWithProviders, setViewportWidth } from '@/test/utils';
import type { MediaSearchResult } from '@/types';

vi.mock('@/lib/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/client')>('@/lib/api/client');
  return { ...actual, apiRequest: vi.fn() };
});

const seriesResult: MediaSearchResult = {
  type: 'series',
  provider_id: 121361,
  title: 'Game of Thrones',
  year: 2011,
  overview: 'Noble families fight for control of the Iron Throne.',
  poster_url: null,
  in_library: true,
  library_id: 12,
  requested_seasons: [1],
  request_id: null,
  request_status: null,
};

const stubRoutes = () => {
  vi.mocked(apiRequest).mockImplementation((path: string) => {
    if (path === '/discover/search') {
      return Promise.resolve({ results: [seriesResult] } as never);
    }
    if (path === '/discover/root-folders') {
      return Promise.resolve({ folders: [{ path: '/media/tv', free_space: null }] } as never);
    }
    return Promise.resolve({
      tvdb_id: 121361,
      in_library: true,
      library_id: 12,
      seasons: [
        { season_number: 1, monitored: true, requested: true, request_id: 'req-1' },
        { season_number: 2, monitored: false, requested: false, request_id: null },
      ],
    } as never);
  });
};

const search = async () => {
  await userEvent.type(screen.getByRole('searchbox'), 'thrones');
  await userEvent.click(screen.getByRole('button', { name: 'Search' }));
};

describe('AddRequestPage on a phone', () => {
  beforeEach(() => {
    vi.mocked(apiRequest).mockReset();
    stubRoutes();
    setViewportWidth(MOBILE_WIDTH);
  });

  afterEach(() => {
    setViewportWidth(DESKTOP_WIDTH);
  });

  it('drops the page subtitle and the card synopsis', async () => {
    renderWithProviders(<AddRequestPage />);

    expect(screen.queryByText(/Search TVDB or TMDB/i)).not.toBeInTheDocument();

    await search();

    expect(await screen.findByText('Game of Thrones')).toBeInTheDocument();
    expect(screen.queryByText(/Iron Throne/i)).not.toBeInTheDocument();
  });

  it('keeps the library and request badges, which is why the card is worth reading', async () => {
    renderWithProviders(<AddRequestPage />);
    await search();

    expect(await screen.findByText('In library')).toBeInTheDocument();
    expect(screen.getByText('Requested: Season 1')).toBeInTheDocument();
    // Results can be of either kind, so the card has to say which this is.
    expect(screen.getByText(/📺 Series/)).toBeInTheDocument();
  });

  it('opens the season picker full screen so the checkboxes fit', async () => {
    renderWithProviders(<AddRequestPage />);
    await search();

    await userEvent.click(await screen.findByRole('button', { name: 'Choose seasons' }));

    const dialog = await screen.findByRole('dialog');
    expect(dialog).toHaveAttribute('data-full-screen', 'true');
    expect(await screen.findByRole('checkbox', { name: /Season 2/ })).toBeInTheDocument();
  });

  it('still shows the subtitle and synopsis on a desktop', async () => {
    setViewportWidth(DESKTOP_WIDTH);

    renderWithProviders(<AddRequestPage />);

    expect(screen.getByText(/Search TVDB or TMDB/i)).toBeInTheDocument();

    await search();

    expect(await screen.findByText(/Iron Throne/i)).toBeInTheDocument();
  });
});
