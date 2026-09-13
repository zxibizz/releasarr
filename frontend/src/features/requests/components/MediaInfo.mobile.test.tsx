import { screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { MediaInfo } from '@/features/requests/components/MediaInfo';
import { DESKTOP_WIDTH, MOBILE_WIDTH, renderWithProviders, setViewportWidth } from '@/test/utils';
import type { MediaRequest } from '@/types';

/** A localised title whose longest word alone outruns a phone-width column. */
const LONG_TITLE = 'Ты и я — полные противоположности';

const series: MediaRequest = {
  id: '1',
  type: 'series',
  title: LONG_TITLE,
  year: 2026,
  season_number: 2,
  total_episodes: 13,
  series_title: 'You and I Are Polar Opposites',
  series_year: 2026,
  imdb_id: 'tt1234567',
  poster_url: 'https://example.test/poster.jpg',
  overview: 'Two opposites grow closer.',
  genres: ['Animation', 'Anime'],
  status: 'downloading',
  created_at: '2026-09-12T00:00:00.000Z',
  updated_at: '2026-09-12T00:00:00.000Z',
};

function renderMediaInfo() {
  return renderWithProviders(<MediaInfo request={series} onManageSeasons={() => {}} />);
}

describe('MediaInfo on a phone', () => {
  beforeEach(() => {
    setViewportWidth(MOBILE_WIDTH);
  });

  afterEach(() => {
    setViewportWidth(DESKTOP_WIDTH);
  });

  it('shows the whole title, long words included', () => {
    renderMediaInfo();

    // A step down from `h2` plus a mid-word wrap: at the larger size the last
    // word of a title like this one ran off the edge of the card.
    const title = screen.getByRole('heading', { level: 3, name: LONG_TITLE });
    expect(title).toHaveClass('break-anywhere');
    expect(title).not.toHaveAttribute('data-line-clamp');
  });

  it('gives the season button and status a row of their own', () => {
    renderMediaInfo();

    const posterRow = screen.getByRole('img').parentElement;
    expect(posterRow).toContainElement(screen.getByRole('heading', { level: 3 }));
    expect(posterRow).not.toContainElement(screen.getByRole('button', { name: 'Manage seasons' }));
  });

  it('keeps the larger title and the season button beside it on a desktop', () => {
    setViewportWidth(DESKTOP_WIDTH);

    renderMediaInfo();

    expect(screen.getByRole('heading', { level: 2, name: LONG_TITLE })).toBeInTheDocument();

    const posterRow = screen.getByRole('img').parentElement;
    expect(posterRow).toContainElement(screen.getByRole('button', { name: 'Manage seasons' }));
  });

  it('names the series in the meta line while the heading shows a translation', () => {
    renderMediaInfo();

    // Sonarr's own title, which the translated heading is not saying.
    expect(
      screen.getByText('📺 Series · You and I Are Polar Opposites · 2026 · Season 2 · 13 episodes'),
    ).toBeInTheDocument();
  });
});
