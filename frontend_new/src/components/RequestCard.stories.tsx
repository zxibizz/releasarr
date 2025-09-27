import type { Meta, StoryObj } from '@storybook/react';

import type { MediaRequest } from '@/types';

import { RequestCard } from './RequestCard';

const movieRequest: MediaRequest = {
  id: 'req-movie-1',
  title: 'The Quantum Enigma',
  year: 2024,
  poster_url: 'https://via.placeholder.com/320x480.png?text=Quantum+Enigma',
  overview:
    'A brilliant physicist risks everything to decode a cosmic signal that could rewrite the laws of reality.',
  genres: ['Sci-Fi', 'Thriller', 'Drama'],
  status: 'completed',
  created_at: new Date('2024-06-12T10:30:00Z').toISOString(),
  updated_at: new Date('2024-07-01T08:15:00Z').toISOString(),
  type: 'movie',
  runtime: 127,
  imdb_id: 'tt1234567',
};

const seriesRequest: MediaRequest = {
  id: 'req-series-1',
  title: 'Echoes of Andromeda',
  year: 2023,
  poster_url: 'https://via.placeholder.com/320x480.png?text=Echoes+of+Andromeda',
  overview:
    'An exploration crew unravels the mysteries of a lost civilization scattered across the Andromeda galaxy.',
  genres: ['Adventure', 'Drama', 'Mystery'],
  status: 'searching',
  created_at: new Date('2023-11-02T19:45:00Z').toISOString(),
  updated_at: new Date('2023-12-15T14:20:00Z').toISOString(),
  type: 'series',
  season_number: 2,
  total_episodes: 10,
  series_title: 'Echoes of Andromeda',
  series_year: 2022,
  imdb_id: 'tt7654321',
};

const meta = {
  title: 'Requests/RequestCard',
  component: RequestCard,
  parameters: {
    layout: 'centered',
  },
  args: {
    request: movieRequest,
  },
} satisfies Meta<typeof RequestCard>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Movie: Story = {
  args: {
    request: movieRequest,
  },
};

export const Series: Story = {
  args: {
    request: seriesRequest,
  },
};
