import type { ConnectionTestPayload, SettingFieldInfo } from '@/types';

/** The services that get a panel of their own, in the order they are shown. */
export const SERVICE_INTEGRATIONS = ['sonarr', 'radarr', 'prowlarr', 'qbittorrent'] as const;

/** The metadata providers, which get the same treatment on their own page. */
export const METADATA_PROVIDERS = ['tvdb', 'tmdb'] as const;

export type ServiceIntegration = (typeof SERVICE_INTEGRATIONS)[number];
export type MetadataProvider = (typeof METADATA_PROVIDERS)[number];
export type PanelIntegration = ServiceIntegration | MetadataProvider;

/**
 * The registry groups fields by section alone, so an integration is identified
 * by the prefix on its keys — which deliberately spans sections: a service's
 * credentials live in `services`, its timeouts in `network`.
 */
export function fieldsForIntegration(
  fields: SettingFieldInfo[],
  integration: PanelIntegration,
): SettingFieldInfo[] {
  return fields.filter((field) => field.key.startsWith(`${integration}_`));
}

export function isServiceScopedKey(key: string): boolean {
  return SERVICE_INTEGRATIONS.some((integration) => key.startsWith(`${integration}_`));
}

/** Where each integration's address is stored; the *arrs and the providers differ. */
const URL_KEYS: Record<PanelIntegration, string> = {
  sonarr: 'sonarr_url',
  radarr: 'radarr_url',
  prowlarr: 'prowlarr_url',
  qbittorrent: 'qbittorrent_url',
  tvdb: 'tvdb_base_url',
  tmdb: 'tmdb_base_url',
};

const LABEL_KEYS: Record<PanelIntegration, string> = {
  sonarr: 'settings.services.sonarr',
  radarr: 'settings.services.radarr',
  prowlarr: 'settings.services.prowlarr',
  qbittorrent: 'settings.services.qbittorrent',
  tvdb: 'settings.metadata.tvdb',
  tmdb: 'settings.metadata.tmdb',
};

/** What each integration needs before it can be reached at all. */
const REQUIRED_KEYS: Record<PanelIntegration, readonly string[]> = {
  sonarr: ['sonarr_url', 'sonarr_api_key'],
  radarr: ['radarr_url', 'radarr_api_key'],
  prowlarr: ['prowlarr_url', 'prowlarr_api_key'],
  qbittorrent: ['qbittorrent_url'],
  tvdb: ['tvdb_base_url', 'tvdb_api_key'],
  tmdb: ['tmdb_base_url', 'tmdb_api_key'],
};

export function urlKeyFor(integration: PanelIntegration): string {
  return URL_KEYS[integration];
}

export function labelKeyFor(integration: PanelIntegration): string {
  return LABEL_KEYS[integration];
}

export function isIntegrationConfigured(
  integration: PanelIntegration,
  valueFor: (key: string) => unknown,
): boolean {
  return REQUIRED_KEYS[integration].every((key) => {
    const value = valueFor(key);
    return typeof value === 'string' && value.trim() !== '';
  });
}

/**
 * Credentials to probe with, taken from the unsaved draft only: the API masks a
 * stored secret, so echoing a loaded value back would test the mask instead.
 * Undefined means "probe whatever is already saved".
 */
export function connectionTestPayload(
  integration: PanelIntegration,
  draft: Record<string, unknown>,
): ConnectionTestPayload | undefined {
  const pick = (key: string) => {
    const value = draft[key];
    return typeof value === 'string' && value !== '' ? value : undefined;
  };

  const payload: ConnectionTestPayload = {
    url: pick(URL_KEYS[integration]),
    api_key: pick(`${integration}_api_key`),
    username: pick(`${integration}_username`),
    password: pick(`${integration}_password`),
  };

  return Object.values(payload).some((value) => value !== undefined) ? payload : undefined;
}
