import { SettingsSectionForm } from '@/features/settings/components/SettingsSectionForm';

export function GeneralSettingsPage() {
  return (
    <SettingsSectionForm
      section="general"
      titleKey="settings.general.title"
      descriptionKey="settings.general.description"
    />
  );
}
