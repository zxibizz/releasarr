import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ReleaseDetailsModal } from '@/features/releases/components/ReleaseDetailsModal';
import { apiRequest } from '@/lib/api/client';
import { renderWithProviders } from '@/test/utils';
import type { MediaRequest, Release, ReleaseFile, ReleaseFileMappingSuggestion } from '@/types';

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

const mappedVideo: ReleaseFile = {
  id: 'f1',
  name: 'Severance.S02E01.1080p.mkv',
  size: 100,
  path: '/d/f1.mkv',
  request_mapping: {
    request_id: 'req-1',
    request_title: 'Severance',
    mapping_type: 'series',
    season: 2,
    episode: 1,
  },
};

const unmappedExtra: ReleaseFile = {
  id: 'f2',
  name: 'readme.nfo',
  size: 10,
  path: '/d/readme.nfo',
};

const secondVideo: ReleaseFile = {
  id: 'f3',
  name: 'Severance.S02E02.1080p.mkv',
  size: 100,
  path: '/d/f3.mkv',
};

const release = (...files: ReleaseFile[]): Release => ({
  id: 'rel-1',
  name: 'Severance.S02.2160p.WEB-DL-FLUX',
  hash: 'abc123',
  size: 12_400_000_000,
  files,
  status: 'completed',
  progress: 100,
  download_speed: 0,
  upload_speed: 0,
  seeders: 10,
  leechers: 1,
  ratio: 1.2,
  added_date: '2026-09-01T00:00:00.000Z',
  completed_date: '2026-09-01T01:00:00.000Z',
  request_ids: ['req-1'],
  torrent_source: 'Indexer A',
  quality: '2160p',
  info_url: 'https://tracker.test/rel/1',
  published_date: '2026-08-30T00:00:00.000Z',
  warnings: [],
});

/** A proposal that disagrees with what the release already holds, so the form is dirty. */
const suggestion: ReleaseFileMappingSuggestion = {
  file_id: 'f1',
  request_mapping: {
    request_id: 'req-1',
    request_title: 'Severance',
    mapping_type: 'series',
    season: 2,
    episode: 5,
  },
};

const MAPPING_PATH = '/releases/rel-1/files/mapping';

const renderModal = (subject: Release, opened = true) =>
  renderWithProviders(
    <ReleaseDetailsModal
      release={subject}
      currentRequest={seriesRequest}
      opened={opened}
      onClose={vi.fn()}
    />,
  );

const openContentTab = () => userEvent.click(screen.getByRole('tab', { name: 'Content' }));

const enterEditMode = async () => {
  await openContentTab();
  await userEvent.click(await screen.findByRole('button', { name: 'Edit mapping' }));
};

describe('ReleaseDetailsModal', () => {
  beforeEach(() => {
    vi.mocked(apiRequest).mockReset();
    vi.mocked(apiRequest).mockImplementation(async (path: string) => {
      if (path === `${MAPPING_PATH}/suggestions`) {
        return { files: [suggestion] };
      }
      if (path === MAPPING_PATH) {
        return { success: true };
      }
      return { requests: [seriesRequest], total: 1 };
    });
  });

  it('opens on what is known about the release', async () => {
    renderModal(release(mappedVideo, unmappedExtra));

    expect(screen.getByRole('tab', { name: 'General' })).toHaveAttribute('aria-selected', 'true');
    expect(await screen.findByText('abc123')).toBeInTheDocument();
    expect(screen.getByText('2160p')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Indexer A/ })).toHaveAttribute(
      'href',
      'https://tracker.test/rel/1',
    );
    expect(screen.getByText('Added')).toBeInTheDocument();

    // Both panels stay mounted, so the files are here but behind the other tab.
    expect(screen.getByText('Severance.S02E01.1080p.mkv')).not.toBeVisible();
  });

  it('names the release in General rather than over the tabs', async () => {
    renderModal(release(mappedVideo));

    expect(await screen.findByRole('dialog')).toHaveAccessibleName('Release details');
    expect(screen.getByText('Severance.S02.2160p.WEB-DL-FLUX')).toBeInTheDocument();
  });

  it('leaves the torrent folder off the file names, since they all share it', async () => {
    const pack: ReleaseFile[] = [
      { ...mappedVideo, name: 'Severance.S02.2160p/Severance.S02E01.1080p.mkv' },
      { ...unmappedExtra, name: 'Severance.S02.2160p/readme.nfo' },
    ];

    renderModal(release(...pack));
    await openContentTab();

    expect(await screen.findByText('Severance.S02E01.1080p.mkv')).toBeInTheDocument();
    expect(screen.queryByText(/Severance\.S02\.2160p\//)).not.toBeInTheDocument();
  });

  it('lists the files and where they are mapped', async () => {
    renderModal(release(mappedVideo, unmappedExtra));
    await openContentTab();

    expect(await screen.findByText('Severance.S02E01.1080p.mkv')).toBeInTheDocument();
    expect(screen.getByText(/Mapping: Severance — S02E01/)).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Other files (1)' }));
    expect(await screen.findByText('readme.nfo')).toBeInTheDocument();
    expect(screen.getByText(/Not mapped/)).toBeInTheDocument();
  });

  it('turns the list editable from the Content tab', async () => {
    renderModal(release(mappedVideo, unmappedExtra));
    await enterEditMode();

    expect(await screen.findByRole('combobox', { name: 'Request' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Edit mapping' })).not.toBeInTheDocument();
    // The release knows which request it belongs to, so nothing asks again.
    expect(
      screen.queryByRole('combobox', { name: /apply request to all/i }),
    ).not.toBeInTheDocument();
  });

  it('stores the mappings and hands the list back', async () => {
    renderModal(release(mappedVideo, unmappedExtra));
    await enterEditMode();

    await screen.findByRole('combobox', { name: 'Request' });
    await userEvent.click(await screen.findByRole('button', { name: /save mappings/i }));

    await waitFor(() =>
      expect(apiRequest).toHaveBeenCalledWith(MAPPING_PATH, {
        method: 'PUT',
        body: { files: [{ file_id: 'f1', request_mapping: suggestion.request_mapping }] },
      }),
    );

    expect(await screen.findByRole('button', { name: 'Edit mapping' })).toBeInTheDocument();
  });

  it('numbers the files automapping cannot place on the release own request', async () => {
    // Nothing to propose: these are the files the backend cannot read an episode
    // number out of, which is exactly when a person reaches for the button.
    vi.mocked(apiRequest).mockImplementation(async (path: string) => {
      if (path === `${MAPPING_PATH}/suggestions`) {
        return { files: [] };
      }
      if (path === MAPPING_PATH) {
        return { success: true };
      }
      return { requests: [seriesRequest], total: 1 };
    });

    renderModal(release(mappedVideo, secondVideo));
    await enterEditMode();

    expect(await screen.findByText('Mapped')).toBeInTheDocument();
    await userEvent.click(await screen.findByRole('button', { name: 'Map automatically' }));

    // The mapped file is numbered back onto what it already had; the unplaced one
    // carries on from it rather than being left blank.
    expect(await screen.findByText(/1 unsaved change/)).toBeInTheDocument();
    expect(screen.getAllByText('Mapped')).toHaveLength(2);
    expect(screen.queryByText(/Current:/)).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /save mappings/i }));
    await waitFor(() =>
      expect(apiRequest).toHaveBeenCalledWith(MAPPING_PATH, {
        method: 'PUT',
        body: {
          files: [
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
              file_id: 'f3',
              request_mapping: {
                request_id: 'req-1',
                request_title: 'Severance',
                mapping_type: 'series',
                season: 2,
                episode: 2,
              },
            },
          ],
        },
      }),
    );
  });

  it('asks before throwing away unsaved mappings', async () => {
    renderModal(release(mappedVideo, unmappedExtra));
    await enterEditMode();

    expect(await screen.findByText(/1 unsaved change/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Cancel' }));

    expect(await screen.findByText('Discard mapping changes')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Discard' }));

    expect(await screen.findByRole('button', { name: 'Edit mapping' })).toBeInTheDocument();
  });

  it('offers nothing to map when the release holds no files', async () => {
    renderModal(release());
    await openContentTab();

    expect(await screen.findByText('No files to list')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Edit mapping' })).not.toBeInTheDocument();
  });

  it('starts again on General when the window is reopened', async () => {
    const subject = release(mappedVideo);
    const { rerender } = renderModal(subject);

    await openContentTab();
    expect(screen.getByRole('tab', { name: 'Content' })).toHaveAttribute('aria-selected', 'true');

    const modal = (opened: boolean) => (
      <ReleaseDetailsModal
        release={subject}
        currentRequest={seriesRequest}
        opened={opened}
        onClose={vi.fn()}
      />
    );

    rerender(modal(false));
    rerender(modal(true));

    expect(await screen.findByRole('tab', { name: 'General' })).toHaveAttribute(
      'aria-selected',
      'true',
    );
  });
});
