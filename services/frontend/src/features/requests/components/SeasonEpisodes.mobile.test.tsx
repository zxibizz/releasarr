import { screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { SeasonEpisodes } from '@/features/requests/components/SeasonEpisodes';
import { apiRequest } from '@/lib/api/client';
import { DESKTOP_WIDTH, MOBILE_WIDTH, renderWithProviders, setViewportWidth } from '@/test/utils';
import type { SeasonEpisode } from '@/types';

vi.mock('@/lib/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/client')>('@/lib/api/client');
  return { ...actual, apiRequest: vi.fn() };
});

const episodes: SeasonEpisode[] = [
  {
    episode_number: 1,
    title: 'Hello, Ms. Cobel',
    status: 'downloaded',
    air_date: '2026-03-01T01:00:00Z',
    file_size: 2 * 1024 ** 3,
  },
  {
    episode_number: 2,
    title: 'Sweet Vitriol',
    status: 'unaired',
    air_date: null,
    file_size: null,
  },
];

const renderEpisodes = () => renderWithProviders(<SeasonEpisodes requestId="req-2" />);

describe('SeasonEpisodes on a phone', () => {
  beforeEach(() => {
    setViewportWidth(MOBILE_WIDTH);
    vi.mocked(apiRequest).mockResolvedValue({ season_number: 2, episodes } as never);
  });

  afterEach(() => {
    setViewportWidth(DESKTOP_WIDTH);
    vi.resetAllMocks();
  });

  it('folds each episode into a row of its own instead of a wide table', async () => {
    renderEpisodes();

    // Five columns cannot fit a phone, and a table that does not fit is a table
    // that scrolls sideways.
    expect(await screen.findByText('1. Hello, Ms. Cobel')).toBeInTheDocument();
    expect(screen.queryByRole('table')).not.toBeInTheDocument();

    // The date and size move to a second line rather than being dropped.
    expect(screen.getByText('Mar 1, 2026 · 2 GB')).toBeInTheDocument();
    expect(screen.getByText('Downloaded')).toBeInTheDocument();
  });

  it('says so when an episode has neither a date nor a file', async () => {
    renderEpisodes();

    expect(await screen.findByText('Not scheduled')).toBeInTheDocument();
    expect(screen.getByText('Not aired')).toBeInTheDocument();
  });

  it('lays the episodes out as a table once there is room for one', async () => {
    setViewportWidth(DESKTOP_WIDTH);

    renderEpisodes();

    expect(await screen.findByRole('table')).toBeInTheDocument();
    expect(screen.getByText('Hello, Ms. Cobel')).toBeInTheDocument();
  });
});
