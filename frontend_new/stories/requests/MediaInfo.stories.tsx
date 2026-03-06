import type { Meta, StoryObj } from '@storybook/react';

import { MediaInfo } from '@/features/requests/MediaInfo';
import type { MediaRequest } from '@/types';

const baseMovieRequest: MediaRequest = {
  id: 'req-movie-001',
  title: 'The Aurora Paradox',
  year: 2025,
  poster_url: 'https://via.placeholder.com/320x480.png?text=Aurora+Paradox',
  overview:
    'A team of scientists races against time to decode a cosmic signal that could prevent an interstellar catastrophe.',
  genres: ['Sci-Fi', 'Thriller', 'Adventure'],
  status: 'downloading',
  created_at: '2025-02-21T14:12:00Z',
  updated_at: '2025-02-23T09:45:00Z',
  type: 'movie',
  runtime: 142,
  imdb_id: 'tt1234567',
};

const baseSeriesRequest: MediaRequest = {
  id: 'req-series-001',
  title: 'Echoes of Atlantis',
  year: 2024,
  poster_url: 'https://via.placeholder.com/320x480.png?text=Echoes+of+Atlantis',
  overview:
    'Explorers uncover relics hinting at an ancient civilization capable of bending time, rekindling a conflict long thought lost.',
  genres: ['Adventure', 'Mystery', 'Drama'],
  status: 'completed',
  created_at: '2024-11-10T18:30:00Z',
  updated_at: '2025-01-04T12:05:00Z',
  type: 'series',
  season_number: 2,
  total_episodes: 10,
  series_title: 'Echoes of Atlantis',
  series_year: 2023,
  imdb_id: 'tt7654321',
};

const meta = {
  title: 'Requests/MediaInfo',
  component: MediaInfo,
  parameters: {
    layout: 'centered',
  },
  args: {
    request: baseMovieRequest,
  },
} satisfies Meta<typeof MediaInfo>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Movie: Story = {
  args: {
    request: baseMovieRequest,
  },
};

export const Series: Story = {
  args: {
    request: baseSeriesRequest,
  },
};
