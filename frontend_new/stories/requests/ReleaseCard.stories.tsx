import type { Meta, StoryObj } from '@storybook/react';
import { fn } from '@storybook/test';

import ReleaseCard from '@/features/requests/components/ReleaseCard';
import type { Release, ReleaseFile } from '@/types';

const buildFile = (overrides: Partial<ReleaseFile> = {}): ReleaseFile => ({
  id: `file-${overrides.id ?? Math.random().toString(36).slice(2)}`,
  name: overrides.name ?? 'Episode.mkv',
  size: overrides.size ?? 2_147_483_648,
  path: overrides.path ?? '/downloads/episode.mkv',
  request_mapping: overrides.request_mapping,
});

const baseRelease: Release = {
  id: 'rel-001',
  name: 'The Aurora Paradox 2160p WEB-DL',
  hash: 'abcdef1234567890',
  size: 8_589_934_592,
  status: 'downloading',
  progress: 64.2,
  download_speed: 12_000_000,
  upload_speed: 4_500_000,
  seeders: 182,
  leechers: 67,
  ratio: 1.42,
  added_date: '2025-02-23T08:12:00Z',
  completed_date: undefined,
  request_ids: ['req-movie-001'],
  torrent_source: 'LunaTrack',
  quality: 'WEB-DL 2160p',
  files: [
    buildFile({
      name: 'The.Aurora.Paradox.2160p.WEB-DL.DDP5.1.x265.mkv',
    }),
  ],
};

const requestSummaries = {
  'req-movie-001': {
    id: 'req-movie-001',
    title: 'The Aurora Paradox',
    year: 2025,
    type: 'movie' as const,
  },
  'req-series-001': {
    id: 'req-series-001',
    title: 'Echoes of Atlantis',
    year: 2024,
    type: 'series' as const,
  },
};

const meta = {
  title: 'Requests/ReleaseCard',
  component: ReleaseCard,
  args: {
    onPause: fn(),
    onResume: fn(),
    onDelete: fn(),
    onViewFiles: fn(),
    requestSummaries,
    currentRequestId: 'req-movie-001',
  },
  parameters: {
    layout: 'centered',
    backgrounds: {
      default: 'app-canvas',
    },
  },
} satisfies Meta<typeof ReleaseCard>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Downloading: Story = {
  args: {
    release: baseRelease,
  },
};

export const Completed: Story = {
  args: {
    release: {
      ...baseRelease,
      id: 'rel-002',
      status: 'completed',
      progress: 100,
      download_speed: 0,
      upload_speed: 8_000_000,
      completed_date: '2025-02-23T14:52:00Z',
    },
  },
};

export const Failed: Story = {
  args: {
    release: {
      ...baseRelease,
      id: 'rel-003',
      status: 'failed',
      progress: 32,
      download_speed: 0,
      upload_speed: 0,
      seeders: 0,
      leechers: 0,
    },
  },
};

export const CompactView: Story = {
  args: {
    release: baseRelease,
    compact: true,
    showActions: false,
  },
};
