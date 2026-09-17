import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { MetadataSettingsPage } from '@/features/settings/pages/MetadataSettingsPage';
import { NetworkSettingsPage } from '@/features/settings/pages/NetworkSettingsPage';
import { ServicesSettingsPage } from '@/features/settings/pages/ServicesSettingsPage';
import { apiRequest } from '@/lib/api/client';
import { renderWithProviders } from '@/test/utils';
import type { SettingFieldInfo, SettingsResponse } from '@/types';

vi.mock('@/lib/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/client')>('@/lib/api/client');
  return { ...actual, apiRequest: vi.fn() };
});

const field = (
  key: string,
  section: SettingFieldInfo['section'],
  kind: string,
  extra: Partial<SettingFieldInfo> = {},
): SettingFieldInfo => ({
  key,
  section,
  kind,
  is_secret: false,
  requires_restart: false,
  locked: false,
  choices: [],
  ...extra,
});

const settings: SettingsResponse = {
  fields: [
    field('sonarr_url', 'services', 'str'),
    field('sonarr_api_key', 'services', 'str', { is_secret: true }),
    field('sonarr_quality_profile_id', 'services', 'int_optional'),
    field('prowlarr_url', 'services', 'str'),
    field('prowlarr_api_key', 'services', 'str', { is_secret: true }),
    field('prowlarr_categories', 'services', 'str_list'),
    field('qbittorrent_url', 'services', 'str'),
    field('qbittorrent_category', 'services', 'str_optional'),
    field('radarr_url', 'services', 'str'),
    field('radarr_api_key', 'services', 'str', { is_secret: true }),
    field('prowlarr_search_retries', 'network', 'int'),
    field('auth_lockout_seconds', 'network', 'int'),
    field('tvdb_base_url', 'metadata', 'str'),
    field('tvdb_api_key', 'metadata', 'str', { is_secret: true }),
    field('tmdb_base_url', 'metadata', 'str'),
    field('tmdb_api_key', 'metadata', 'str', { is_secret: true }),
    field('metadata_languages', 'metadata', 'str_list'),
  ],
  values: {
    services: {
      sonarr_url: 'http://sonarr:8989/api/v3',
      sonarr_api_key: '**********',
      sonarr_quality_profile_id: 4,
      prowlarr_url: 'http://prowlarr:9696/api/v1',
      prowlarr_api_key: '**********',
      prowlarr_categories: ['5000'],
      qbittorrent_url: '',
      qbittorrent_category: null,
      radarr_url: 'http://radarr:7878/api/v3',
      radarr_api_key: '',
    },
    network: { prowlarr_search_retries: 1, auth_lockout_seconds: 900 },
    metadata: {
      tvdb_base_url: 'https://api4.thetvdb.com/v4',
      tvdb_api_key: '**********',
      tmdb_base_url: 'https://api.themoviedb.org/3',
      tmdb_api_key: '',
      metadata_languages: ['eng'],
    },
  },
  locked_keys: [],
  pending_restart_keys: [],
};

const QUALITY_PROFILES = { profiles: [{ id: 4, name: 'HD-1080p' }, { id: 6, name: 'Ultra-HD' }] };
const INDEXER_CATEGORIES = { categories: [{ id: 5000, name: 'TV' }, { id: 2000, name: 'Movies' }] };

let optionFailure: string | null = null;

beforeEach(() => {
  optionFailure = null;
  vi.mocked(apiRequest).mockReset();
  vi.mocked(apiRequest).mockImplementation(async (path: string) => {
    if (path === '/settings') return settings;
    if (path.startsWith('/settings/test/'))
      return { integration: 'sonarr', success: true, detail: null };
    if (path.startsWith('/settings/options/')) {
      if (optionFailure) throw new Error(optionFailure);
      if (path.includes('quality-profiles')) return QUALITY_PROFILES;
      if (path.includes('indexer-categories')) return INDEXER_CATEGORIES;
      return { categories: ['releasarr', 'tv'] };
    }
    if (path.startsWith('/settings/')) return settings;
    throw new Error(`Unexpected request: ${path}`);
  });
});

async function openPanel(name: string, page = <ServicesSettingsPage />) {
  const user = userEvent.setup();
  renderWithProviders(page);

  await user.click(await screen.findByRole('button', { name: `Edit ${name}` }));
  return { user, dialog: within(await screen.findByRole('dialog')) };
}

describe('ServicesSettingsPage', () => {
  it('gives each service its own panel rather than one heap of fields', async () => {
    renderWithProviders(<ServicesSettingsPage />);

    for (const name of ['Sonarr', 'Radarr', 'Prowlarr', 'qBittorrent']) {
      expect(await screen.findByRole('button', { name: `Edit ${name}` })).toBeInTheDocument();
    }
    // The flat form is gone: nothing is editable until a panel is opened.
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  });

  it('flags a service that is missing a credential', async () => {
    renderWithProviders(<ServicesSettingsPage />);

    expect(await screen.findByText('Sonarr')).toBeInTheDocument();
    // Radarr has a URL but no API key; qBittorrent has no URL at all.
    expect(screen.getAllByText('Not configured')).toHaveLength(2);
    expect(screen.getAllByText('Configured')).toHaveLength(2);
  });

  it('probes the saved configuration from a panel, without a payload', async () => {
    const user = userEvent.setup();
    renderWithProviders(<ServicesSettingsPage />);

    const panel = (await screen.findByText('Sonarr')).closest('.mantine-Card-root');
    await user.click(within(panel as HTMLElement).getByRole('button', { name: 'Test' }));

    expect(vi.mocked(apiRequest)).toHaveBeenCalledWith('/settings/test/sonarr', { method: 'POST' });
  });
});

describe('the service edit modal', () => {
  it('collects the service tuning that used to sit under Network', async () => {
    const { dialog } = await openPanel('Prowlarr');

    expect(dialog.getByLabelText(/^prowlarr url/i)).toBeInTheDocument();
    expect(dialog.getByLabelText(/^prowlarr search retries/i)).toBeInTheDocument();
    // Another section's field is not this service's business.
    expect(dialog.queryByLabelText(/^lockout duration/i)).not.toBeInTheDocument();
  });

  it('saves across both of the sections its fields live in', async () => {
    const { user, dialog } = await openPanel('Prowlarr');

    await user.clear(dialog.getByLabelText(/^prowlarr url/i));
    await user.type(dialog.getByLabelText(/^prowlarr url/i), 'http://new:9696');
    await user.clear(dialog.getByLabelText(/^prowlarr search retries/i));
    await user.type(dialog.getByLabelText(/^prowlarr search retries/i), '3');
    await user.click(dialog.getByRole('button', { name: 'Save' }));

    const patches = vi
      .mocked(apiRequest)
      .mock.calls.filter(([, options]) => options?.method === 'PATCH');
    expect(patches.map(([path]) => path)).toEqual(['/settings/services', '/settings/network']);
    expect(patches[0][1]?.body).toEqual({ values: { prowlarr_url: 'http://new:9696' } });
    expect(patches[1][1]?.body).toEqual({ values: { prowlarr_search_retries: 3 } });
  });

  it('probes with the edited credentials only, never the masked stored secret', async () => {
    const { user, dialog } = await openPanel('Sonarr');

    await user.clear(dialog.getByLabelText(/^sonarr api key/i));
    await user.type(dialog.getByLabelText(/^sonarr api key/i), 'fresh-key');
    await user.click(dialog.getByRole('button', { name: 'Test' }));

    expect(vi.mocked(apiRequest)).toHaveBeenCalledWith('/settings/test/sonarr', {
      method: 'POST',
      body: { url: undefined, api_key: 'fresh-key', username: undefined, password: undefined },
    });
  });
});

describe('NetworkSettingsPage', () => {
  it('keeps only the settings that belong to no single service', async () => {
    renderWithProviders(<NetworkSettingsPage />);

    expect(await screen.findByLabelText(/^lockout duration/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/^prowlarr search retries/i)).not.toBeInTheDocument();
  });
});

describe('the option pickers', () => {
  it('offers the profiles the *arr reports instead of a bare id box', async () => {
    const { user, dialog } = await openPanel('Sonarr');

    const picker = dialog.getByRole('combobox', { name: /^sonarr quality profile/i });
    expect(picker).toHaveValue('HD-1080p');

    await user.click(picker);
    expect(await screen.findByRole('option', { name: 'Ultra-HD' })).toBeInTheDocument();
  });

  it('saves the picked profile as the number the field holds', async () => {
    const { user, dialog } = await openPanel('Sonarr');

    await user.click(dialog.getByRole('combobox', { name: /^sonarr quality profile/i }));
    await user.click(await screen.findByRole('option', { name: 'Ultra-HD' }));
    await user.click(dialog.getByRole('button', { name: 'Save' }));

    const patch = vi
      .mocked(apiRequest)
      .mock.calls.find(([, options]) => options?.method === 'PATCH');
    expect(patch?.[1]?.body).toEqual({ values: { sonarr_quality_profile_id: 6 } });
  });

  it('names each indexer category rather than asking for the id', async () => {
    const { user, dialog } = await openPanel('Prowlarr');

    await user.click(dialog.getByRole('combobox', { name: /^prowlarr categories/i }));

    expect(await screen.findByRole('option', { name: '2000 — Movies' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: '5000 — TV' })).toBeInTheDocument();
  });

  it('disables the picker and says why when the service cannot answer', async () => {
    optionFailure = 'qBittorrent is not configured';
    const { dialog } = await openPanel('qBittorrent');

    const picker = await dialog.findByRole('combobox', { name: /^qbittorrent category/i });
    expect(picker).toBeDisabled();
    expect(await dialog.findByText('qBittorrent is not configured')).toBeInTheDocument();
  });
});

describe('MetadataSettingsPage', () => {
  it('gives each provider its own panel', async () => {
    renderWithProviders(<MetadataSettingsPage />);

    expect(await screen.findByRole('button', { name: 'Edit TVDB' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Edit TMDB' })).toBeInTheDocument();
    // TMDB has a URL but no key.
    expect(screen.getByText('Not configured')).toBeInTheDocument();
  });

  it('leaves the shared languages field on the page, owned by no provider', async () => {
    renderWithProviders(<MetadataSettingsPage />);

    expect(
      await screen.findByRole('combobox', { name: /^metadata languages/i }),
    ).toBeInTheDocument();
    expect(screen.queryByLabelText(/^tvdb api key/i)).not.toBeInTheDocument();
  });

  it('edits one provider at a time in its own modal', async () => {
    const { dialog } = await openPanel('TVDB', <MetadataSettingsPage />);

    expect(dialog.getByLabelText(/^tvdb base url/i)).toBeInTheDocument();
    expect(dialog.queryByLabelText(/^tmdb base url/i)).not.toBeInTheDocument();
    expect(dialog.queryByLabelText(/^metadata languages/i)).not.toBeInTheDocument();
  });
});
