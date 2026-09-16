import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { FileMappingForm } from '@/features/releases/fileMapping/FileMappingForm';
import { apiRequest } from '@/lib/api/client';
import { renderWithProviders } from '@/test/utils';
import type { MediaRequest, ReleaseFile, ReleaseFileMappingSuggestion } from '@/types';

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
  { id: 'f2', name: 'Severance.S02E02.1080p.mkv', size: 200, path: '/d/f2.mkv' },
  { id: 'f3', name: 'readme.txt', size: 10, path: '/d/readme.txt' },
  { id: 'f1', name: 'Severance.S02E01.1080p.mkv', size: 100, path: '/d/f1.mkv' },
];

const suggestion = (fileId: string, episode: number): ReleaseFileMappingSuggestion => ({
  file_id: fileId,
  request_mapping: {
    request_id: 'req-1',
    request_title: 'Severance',
    mapping_type: 'series',
    season: 2,
    episode,
  },
});

const MAPPING_PATH = '/releases/rel-1/files/mapping';

const renderForm = () =>
  renderWithProviders(<FileMappingForm releaseId="rel-1" requestId="req-1" files={files} />);

describe('FileMappingForm', () => {
  beforeEach(() => {
    vi.mocked(apiRequest).mockReset();
    vi.mocked(apiRequest).mockImplementation(async (path: string) => {
      if (path === `${MAPPING_PATH}/suggestions`) {
        return { files: [suggestion('f1', 1), suggestion('f2', 2)] };
      }
      if (path === MAPPING_PATH) {
        return { success: true };
      }
      return { requests: [seriesRequest], total: 1 };
    });
  });

  it("lists video files by name and seeds season/episode from the server's suggestions", async () => {
    renderForm();

    expect(await screen.findByText('Severance.S02E01.1080p.mkv')).toBeInTheDocument();
    expect(screen.getByText('Severance.S02E02.1080p.mkv')).toBeInTheDocument();
    expect(screen.queryByText('readme.txt')).not.toBeInTheDocument();

    const episodeInputs = await waitFor(() => {
      const inputs = screen.getAllByLabelText('Episode');
      expect(inputs).toHaveLength(2);
      return inputs;
    });
    expect(episodeInputs[0]).toHaveValue('1');
    expect(episodeInputs[1]).toHaveValue('2');
  });

  it('reports the suggestions as unsaved, since nothing has stored them', async () => {
    renderForm();

    expect(await screen.findByText(/2 unsaved change/)).toBeInTheDocument();
  });

  it('maps to the request it was opened for, without asking which one', async () => {
    renderForm();

    await screen.findByText('Severance.S02E01.1080p.mkv');

    expect(
      screen.queryByRole('combobox', { name: /apply request to all/i }),
    ).not.toBeInTheDocument();

    // Held back until the automapper's proposals are in, so a tap cannot blank
    // the stored mappings for a list that is about to change underneath it.
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Map automatically' })).toBeEnabled(),
    );
  });

  it('keeps non-video files behind a collapsed section', async () => {
    const user = userEvent.setup();
    renderForm();

    await screen.findByText('Severance.S02E01.1080p.mkv');
    await user.click(screen.getByRole('button', { name: 'Other files (1)' }));

    expect(await screen.findByText('readme.txt')).toBeInTheDocument();
  });

  it('sends the mapped files to the API when saving', async () => {
    const user = userEvent.setup();
    renderForm();

    await screen.findByText('Severance.S02E01.1080p.mkv');
    await waitFor(() => expect(screen.getAllByLabelText('Episode')).toHaveLength(2));

    await user.click(screen.getByRole('button', { name: /save mappings/i }));

    await waitFor(() => {
      expect(vi.mocked(apiRequest)).toHaveBeenCalledWith(
        MAPPING_PATH,
        expect.objectContaining({ method: 'PUT' }),
      );
    });

    const call = vi.mocked(apiRequest).mock.calls.find(([path]) => path === MAPPING_PATH);
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
    ]);
  });
});
