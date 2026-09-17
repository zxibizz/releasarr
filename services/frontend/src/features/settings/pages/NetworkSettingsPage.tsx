import { SettingsSectionForm } from '@/features/settings/components/SettingsSectionForm';
import { isServiceScopedKey } from '@/features/settings/serviceFields';

export function NetworkSettingsPage() {
  return (
    <SettingsSectionForm
      section="network"
      titleKey="settings.network.title"
      descriptionKey="settings.network.description"
      // Each service's timeouts belong to that service's panel, not to a list
      // of unrelated knobs the reader has to know the prefix of.
      includeField={(field) => !isServiceScopedKey(field.key)}
    />
  );
}
