import { SettingsSectionForm } from '@/features/settings/components/SettingsSectionForm';

export function NetworkSettingsPage() {
  return (
    <SettingsSectionForm
      section="network"
      titleKey="settings.network.title"
      descriptionKey="settings.network.description"
    />
  );
}
