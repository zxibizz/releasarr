import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { FileMappingForm } from '@/features/releases/fileMapping/FileMappingForm';
import { apiRequest } from '@/lib/api/client';
import { renderWithProviders } from '@/test/utils';
import type { MediaRequest, ReleaseFile } from '@/types';

vi.mock('@/lib/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/client')>('@/lib/api/client');
  return { ...actual, apiRequest: vi.fn() };
});

const seriesRequest: MediaRequest = {
  id: 'req-1',
  type: 'series',
  title: 'Severance',
  year: 2022,
  season_number: 2,
  total_episodes: 10,
  series_title: 'Severance',
  series_year: 2022,
  imdb_id: 'tt1',
  poster_url: 'https://example.test/p.jpg',
  overview: '',
  genres: [],
  status: 'downloading',
  created_at: '2026-01-01T00:00:00.000Z',
  updated_at: '2026-01-01T00:00:00.000Z',
};

const files: ReleaseFile[] = [
  { id: 'f1', name: 'Severance.S02E01.1080p.mkv', size: 100, path: '/d/f1.mkv' },
  { id: 'f2', name: 'Severance.S02E02.1080p.mkv', size: 200, path: '/d/f2.mkv' },
  { id: 'f3', name: 'readme.txt', size: 10, path: '/d/readme.txt' },
];

const renderForm = () =>
  renderWithProviders(
    <FileMappingForm
      releaseId="rel-1"
      requestId="req-1"
      files={files}
      defaultRequest={{ id: 'req-1', title: 'Severance', type: 'series', seasonNumber: 2 }}
    />,
  );

describe('FileMappingForm', () => {
  beforeEach(() => {
    vi.mocked(apiRequest).mockReset();
    vi.mocked(apiRequest).mockResolvedValue({ requests: [seriesRequest], total: 1 });
  });

  it('lists only video files by default and seeds season/episode from filenames', async () => {
    renderForm();

    expect(await screen.findByText('Severance.S02E01.1080p.mkv')).toBeInTheDocument();
    expect(screen.getByText('Severance.S02E02.1080p.mkv')).toBeInTheDocument();
    expect(screen.queryByText('readme.txt')).not.toBeInTheDocument();

    const episodeInputs = screen.getAllByLabelText('Episode');
    expect(episodeInputs[0]).toHaveValue('1');
    expect(episodeInputs[1]).toHaveValue('2');
  });

  it('sends the mapped files to the API when saving', async () => {
    const user = userEvent.setup();
    renderForm();

    await screen.findByText('Severance.S02E01.1080p.mkv');
    vi.mocked(apiRequest).mockResolvedValueOnce({ success: true });

    await user.click(screen.getByRole('button', { name: /save mappings/i }));

    await waitFor(() => {
      expect(vi.mocked(apiRequest)).toHaveBeenCalledWith(
        '/releases/rel-1/files/mapping',
        expect.objectContaining({ method: 'PUT' }),
      );
    });

    const call = vi
      .mocked(apiRequest)
      .mock.calls.find(([path]) => path === '/releases/rel-1/files/mapping');
    const body = call?.[1]?.body as { files: unknown[] };

    expect(body.files).toEqual([
      {
        file_id: 'f1',
        request_mapping: {
          request_id: 'req-1',
          request_title: 'Severance',
          mapping_type: 'series',
          season: 2,
          episode: 1,
        },
      },
      {
        file_id: 'f2',
        request_mapping: {
          request_id: 'req-1',
          request_title: 'Severance',
          mapping_type: 'series',
          season: 2,
          episode: 2,
        },
      },
      {
        file_id: 'f3',
        request_mapping: {
          request_id: 'req-1',
          request_title: 'Severance',
          mapping_type: 'series',
          season: 2,
          episode: 1,
        },
      },
    ]);
  });
});
