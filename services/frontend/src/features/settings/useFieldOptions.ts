import { useTranslation } from 'react-i18next';

import type { FieldOptions } from '@/features/settings/components/SettingsField';
import {
  useDownloadCategories,
  useIndexerCategories,
  useQualityProfiles,
} from '@/features/settings/queries';
import type { PanelIntegration } from '@/features/settings/serviceFields';
import { getErrorMessage } from '@/utils/errors';
import type { SettingFieldInfo } from '@/types';

/**
 * Turns the fields whose values another service owns into pickers.
 *
 * Every lookup is declared, and only the one this integration needs is enabled:
 * hooks cannot be called conditionally, and an idle query costs nothing.
 */
export function useFieldOptions(
  integration: PanelIntegration,
): (field: SettingFieldInfo) => FieldOptions | undefined {
  const { t } = useTranslation();
  const isArr = integration === 'sonarr' || integration === 'radarr';

  const profiles = useQualityProfiles(isArr ? integration : 'sonarr', isArr);
  const indexerCategories = useIndexerCategories(integration === 'prowlarr');
  const downloadCategories = useDownloadCategories(integration === 'qbittorrent');

  const failure = (error: unknown) =>
    error ? getErrorMessage(error, t('settings.options.failed')) : null;

  return (field: SettingFieldInfo) => {
    switch (field.key) {
      case 'sonarr_quality_profile_id':
      case 'radarr_quality_profile_id':
        return {
          items: (profiles.data ?? []).map((profile) => ({
            value: String(profile.id),
            label: profile.name,
          })),
          loading: profiles.isFetching,
          error: failure(profiles.error),
        };
      case 'prowlarr_categories':
        return {
          items: (indexerCategories.data ?? []).map((category) => ({
            value: String(category.id),
            label: `${category.id} — ${category.name}`,
          })),
          loading: indexerCategories.isFetching,
          error: failure(indexerCategories.error),
        };
      case 'qbittorrent_category':
        return {
          items: (downloadCategories.data ?? []).map((name) => ({ value: name, label: name })),
          loading: downloadCategories.isFetching,
          error: failure(downloadCategories.error),
        };
      default:
        return undefined;
    }
  };
}
