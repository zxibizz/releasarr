import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ReleaseSearch } from '@/features/releases/components/ReleaseSearch';
import { apiRequest } from '@/lib/api/client';
import { renderWithProviders } from '@/test/utils';
import type { IndexerSearchFailure, ReleaseSearchResult, SearchIndexer } from '@/types';

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

const second: ReleaseSearchResult = {
  ...candidate,
  release_id: 'r2',
  release_name: 'Severance.S02E01.1080p.WEB-DL-OTHER',
  source: 'Indexer B',
};

const answer = (results: ReleaseSearchResult[], failed: IndexerSearchFailure[] = []) => ({
  results,
  query: 'Severance S02E01',
  total_results: results.length,
  failed_indexers: failed,
  searched_indexers: 1,
});

type Reply = () => Promise<unknown>;

/** Answers the indexer list, then each indexer's own search from `byIndexer`. */
function mockIndexers(indexers: SearchIndexer[], byIndexer: Record<number, Reply>) {
  vi.mocked(apiRequest).mockImplementation(async (path, options) => {
    if (path === '/releases/search/indexers') return { indexers };
    if (path === '/releases/search') {
      const indexerId = options?.query?.indexer_id as number;
      return byIndexer[indexerId]();
    }
    return { releases: [] };
  });
}

describe('ReleaseSearch failed indexers', () => {
  beforeEach(() => {
    vi.mocked(apiRequest).mockReset();
  });

  it('shows an alert naming the indexers that did not respond', async () => {
    mockIndexers(
      [
        { indexer_id: 1, name: 'Indexer A' },
        { indexer_id: 2, name: 'Flaky Indexer' },
      ],
      {
        1: async () => answer([candidate]),
        2: async () =>
          answer([], [{ indexer_id: 2, name: 'Flaky Indexer', reason: 'timed out after 45.0s' }]),
      },
    );

    renderSearch();
    await runSearch();

    expect(await screen.findByText('Flaky Indexer', { exact: false })).toBeInTheDocument();
  });

  it('renders no alert when every indexer answered', async () => {
    mockIndexers([{ indexer_id: 1, name: 'Indexer A' }], {
      1: async () => answer([candidate]),
    });

    renderSearch();
    await runSearch();

    await screen.findByText(candidate.release_name);
    expect(screen.queryByText('Flaky Indexer', { exact: false })).not.toBeInTheDocument();
  });

  it('reports an indexer whose request failed and keeps the others', async () => {
    mockIndexers(
      [
        { indexer_id: 1, name: 'Indexer A' },
        { indexer_id: 2, name: 'Broken Indexer' },
      ],
      {
        1: async () => answer([candidate]),
        2: async () => {
          throw new Error('Bad gateway');
        },
      },
    );

    renderSearch();
    await runSearch();

    expect(await screen.findByText(candidate.release_name)).toBeInTheDocument();
    expect(await screen.findByText('Broken Indexer', { exact: false })).toBeInTheDocument();
  });

  it('shows the search as failed when no indexer could be asked', async () => {
    mockIndexers([{ indexer_id: 1, name: 'Indexer A' }], {
      1: async () => {
        throw new Error('Bad gateway');
      },
    });

    renderSearch();
    await runSearch();

    expect(await screen.findByRole('alert')).toBeInTheDocument();
    expect(screen.queryByText('Some indexers did not respond')).not.toBeInTheDocument();
  });
});

describe('ReleaseSearch with a slow indexer', () => {
  beforeEach(() => {
    vi.mocked(apiRequest).mockReset();
  });

  it('shows the fast indexers while the slow one is still answering', async () => {
    let finishSlow: (value: unknown) => void = () => {};
    mockIndexers(
      [
        { indexer_id: 1, name: 'Fast Indexer' },
        { indexer_id: 2, name: 'Slow Indexer' },
      ],
      {
        1: async () => answer([candidate]),
        2: () =>
          new Promise((resolve) => {
            finishSlow = resolve;
          }),
      },
    );

    renderSearch();
    await runSearch();

    expect(await screen.findByText(candidate.release_name)).toBeInTheDocument();
    expect(screen.getByText('Waiting for Slow Indexer…')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Search' })).not.toHaveAttribute('data-loading');

    finishSlow(answer([second]));

    expect(await screen.findByText(second.release_name)).toBeInTheDocument();
    expect(screen.queryByText('Waiting for Slow Indexer…')).not.toBeInTheDocument();
    expect(screen.getByText(candidate.release_name)).toBeInTheDocument();
  });

  it('drops a slow answer once the search has been cleared', async () => {
    let finishSlow: (value: unknown) => void = () => {};
    mockIndexers(
      [
        { indexer_id: 1, name: 'Fast Indexer' },
        { indexer_id: 2, name: 'Slow Indexer' },
      ],
      {
        1: async () => answer([candidate]),
        2: () =>
          new Promise((resolve) => {
            finishSlow = resolve;
          }),
      },
    );

    renderSearch();
    await runSearch();
    await screen.findByText(candidate.release_name);

    await userEvent.click(screen.getByRole('button', { name: 'Clear' }));
    finishSlow(answer([second]));

    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(screen.queryByText(second.release_name)).not.toBeInTheDocument();
    expect(screen.queryByText('Waiting for Slow Indexer…')).not.toBeInTheDocument();
  });
});
