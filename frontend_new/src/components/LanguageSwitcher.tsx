import { Box, Select, VisuallyHidden } from '@chakra-ui/react';
import React from 'react';
import { useTranslation } from 'react-i18next';

import { supportedLocales, type AppLocale } from '@/locales/resources';

export const LanguageSwitcher: React.FC = () => {
  const { i18n, t } = useTranslation();

  const currentLocale = supportedLocales.includes(i18n.language as AppLocale)
    ? (i18n.language as AppLocale)
    : ((i18n.resolvedLanguage as AppLocale | undefined) ?? supportedLocales[0]);

  const handleChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    void i18n.changeLanguage(event.target.value);
  };

  return (
    <Box>
      <VisuallyHidden as="label" htmlFor="language-select">
        {t('nav.languageLabel')}
      </VisuallyHidden>
      <Select
        id="language-select"
        size="sm"
        width="auto"
        value={currentLocale}
        onChange={handleChange}
        bg="rgba(15, 23, 42, 0.7)"
        borderColor="border.muted"
        _hover={{ borderColor: 'brand.400' }}
      >
        {supportedLocales.map((locale) => (
          <option key={locale} value={locale}>
            {t(`nav.languages.${locale}`)}
          </option>
        ))}
      </Select>
    </Box>
  );
};

export default LanguageSwitcher;
