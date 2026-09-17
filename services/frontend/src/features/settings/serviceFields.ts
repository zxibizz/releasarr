import type { ConnectionTestPayload, SettingFieldInfo } from '@/types';

/** The services that get a panel of their own, in the order they are shown. */
export const SERVICE_INTEGRATIONS = ['sonarr', 'radarr', 'prowlarr', 'qbittorrent'] as const;

export type ServiceIntegration = (typeof SERVICE_INTEGRATIONS)[number];

/**
 * The registry groups fields by section alone, so a service is identified by the
 * prefix on its keys — which deliberately spans sections: the credentials live
 * in `services`, that service's timeouts in `network`.
 */
export function fieldsForService(
  fields: SettingFieldInfo[],
  integration: ServiceIntegration,
): SettingFieldInfo[] {
  return fields.filter((field) => field.key.startsWith(`${integration}_`));
}

export function isServiceScopedKey(key: string): boolean {
  return SERVICE_INTEGRATIONS.some((integration) => key.startsWith(`${integration}_`));
}

/** What each service needs before it can be reached at all. */
const REQUIRED_KEYS: Record<ServiceIntegration, readonly string[]> = {
  sonarr: ['sonarr_url', 'sonarr_api_key'],
  radarr: ['radarr_url', 'radarr_api_key'],
  prowlarr: ['prowlarr_url', 'prowlarr_api_key'],
  qbittorrent: ['qbittorrent_url'],
};

export function isServiceConfigured(
  integration: ServiceIntegration,
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
  integration: ServiceIntegration,
  draft: Record<string, unknown>,
): ConnectionTestPayload | undefined {
  const pick = (suffix: string) => {
    const value = draft[`${integration}_${suffix}`];
    return typeof value === 'string' && value !== '' ? value : undefined;
  };

  const payload: ConnectionTestPayload = {
    url: pick('url'),
    api_key: pick('api_key'),
    username: pick('username'),
    password: pick('password'),
  };

  return Object.values(payload).some((value) => value !== undefined) ? payload : undefined;
}
