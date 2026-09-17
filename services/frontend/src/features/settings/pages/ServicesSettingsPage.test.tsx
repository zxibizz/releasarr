import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

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
    field('prowlarr_url', 'services', 'str'),
    field('prowlarr_api_key', 'services', 'str', { is_secret: true }),
    field('qbittorrent_url', 'services', 'str'),
    field('radarr_url', 'services', 'str'),
    field('radarr_api_key', 'services', 'str', { is_secret: true }),
    field('prowlarr_search_retries', 'network', 'int'),
    field('auth_lockout_seconds', 'network', 'int'),
  ],
  values: {
    services: {
      sonarr_url: 'http://sonarr:8989/api/v3',
      sonarr_api_key: '**********',
      prowlarr_url: 'http://prowlarr:9696/api/v1',
      prowlarr_api_key: '**********',
      qbittorrent_url: '',
      radarr_url: 'http://radarr:7878/api/v3',
      radarr_api_key: '',
    },
    network: { prowlarr_search_retries: 1, auth_lockout_seconds: 900 },
  },
  locked_keys: [],
  pending_restart_keys: [],
};

beforeEach(() => {
  vi.mocked(apiRequest).mockReset();
  vi.mocked(apiRequest).mockImplementation(async (path: string) => {
    if (path === '/settings') return settings;
    if (path.startsWith('/settings/test/')) return { integration: 'sonarr', success: true, detail: null };
    if (path.startsWith('/settings/')) return settings;
    throw new Error(`Unexpected request: ${path}`);
  });
});

async function openPanel(name: string) {
  const user = userEvent.setup();
  renderWithProviders(<ServicesSettingsPage />);

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
