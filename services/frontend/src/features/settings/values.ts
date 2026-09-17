import type { SettingsResponse } from '@/types';

/** Field keys are unique across sections, so the sections flatten into one lookup. */
export function flattenSettingValues(settings: SettingsResponse): Record<string, unknown> {
  return Object.assign({}, ...Object.values(settings.values)) as Record<string, unknown>;
}
