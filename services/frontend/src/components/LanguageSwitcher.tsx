import { Select, type MantineSize, type SelectProps } from '@mantine/core';
import { useTranslation } from 'react-i18next';

import { supportedLocales, type AppLocale } from '@/locales/resources';

interface LanguageSwitcherProps {
  size?: MantineSize;
  w?: SelectProps['w'];
}

export function LanguageSwitcher({ size = 'xs', w = 110 }: LanguageSwitcherProps) {
  const { i18n, t } = useTranslation();

  const currentLocale = supportedLocales.includes(i18n.language as AppLocale)
    ? (i18n.language as AppLocale)
    : ((i18n.resolvedLanguage as AppLocale | undefined) ?? supportedLocales[0]);

  return (
    <Select
      aria-label={t('nav.languageLabel')}
      size={size}
      w={w}
      allowDeselect={false}
      checkIconPosition="right"
      value={currentLocale}
      onChange={(value) => value && void i18n.changeLanguage(value)}
      data={supportedLocales.map((locale) => ({
        value: locale,
        label: t(`nav.languages.${locale}`),
      }))}
    />
  );
}
