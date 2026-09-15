import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ReleaseSearch } from '@/features/releases/components/ReleaseSearch';
import { apiRequest } from '@/lib/api/client';
import { renderWithProviders } from '@/test/utils';
import type { ReleaseSearchResult } from '@/types';

vi.mock('@/lib/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/client')>('@/lib/api/client');
  return { ...actual, apiRequest: vi.fn() };
});

const candidate: ReleaseSearchResult = {
  release_id: 'r1',
  release_name: 'Severance.S02E01.WEBRip-GROUP',
  size: '2.1 GB',
  seeders: 10,
  leechers: 1,
  quality: '1080p',
  source: 'Indexer A',
  publish_date: '2026-09-10T00:00:00.000Z',
};

function renderSearch() {
  return renderWithProviders(
    <ReleaseSearch
      requestId="1"
      requestTitle="Severance"
      prefillQuery="Severance S02E01"
      onDownloadQueued={() => {}}
    />,
  );
}

async function runSearch() {
  await userEvent.click(screen.getByRole('button', { name: 'Search' }));
}

describe('ReleaseSearch failed indexers', () => {
  beforeEach(() => {
    vi.mocked(apiRequest).mockReset();
  });

  it('shows an alert naming the indexers that did not respond', async () => {
    vi.mocked(apiRequest).mockResolvedValue({
      results: [candidate],
      query: 'Severance S02E01',
      total_results: 1,
      failed_indexers: [{ indexer_id: 2, name: 'Flaky Indexer', reason: 'timed out after 10.0s' }],
      searched_indexers: 2,
    });

    renderSearch();
    await runSearch();

    expect(await screen.findByText('Flaky Indexer', { exact: false })).toBeInTheDocument();
  });

  it('renders no alert when every indexer answered', async () => {
    vi.mocked(apiRequest).mockResolvedValue({
      results: [candidate],
      query: 'Severance S02E01',
      total_results: 1,
      failed_indexers: [],
      searched_indexers: 2,
    });

    renderSearch();
    await runSearch();

    await screen.findByText(candidate.release_name);
    expect(screen.queryByText('Flaky Indexer', { exact: false })).not.toBeInTheDocument();
  });
});
