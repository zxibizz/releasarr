import { Button, FormControl, FormLabel, Select, Stack, Text } from '@chakra-ui/react';
import type { ChangeEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { Link as RouterLink } from 'react-router-dom';

import { MediaInfo } from '@/features/requests/MediaInfo';
import type { MediaRequest } from '@/types';

interface RequestHeaderProps {
  request: MediaRequest;
  availableLanguages: string[];
  selectedLanguage: string | null;
  onLanguageChange: (language: string | null) => void;
}

export function RequestHeader({
  request,
  availableLanguages,
  selectedLanguage,
  onLanguageChange,
}: RequestHeaderProps) {
  const { t } = useTranslation();
  const subtitleKey =
    request.type === 'movie' ? 'requestHeader.subtitle.movie' : 'requestHeader.subtitle.series';
  const controlId = `metadata-language-${request.id}`;

  const handleSelectChange = (event: ChangeEvent<HTMLSelectElement>) => {
    const nextValue = event.target.value;
    onLanguageChange(nextValue === 'default' ? null : nextValue);
  };

  const showLanguageSelector = availableLanguages.length > 0;

  return (
    <Stack spacing={8}>
      <Stack
        direction={{ base: 'column', sm: 'row' }}
        spacing={{ base: 3, sm: 4 }}
        align={{ base: 'stretch', sm: 'center' }}
        justify="space-between"
      >
        <Button as={RouterLink} to="/" variant="outline" colorScheme="blue" width="fit-content">
          {t('common.backToRequests')}
        </Button>

        {showLanguageSelector && (
          <FormControl width={{ base: '100%', sm: 'auto' }} maxW="260px">
            <FormLabel htmlFor={controlId} fontSize="sm" color="text.subtle" mb={1}>
              {t('localization.selectorLabel')}
            </FormLabel>
            <Select
              id={controlId}
              size="sm"
              value={selectedLanguage ?? 'default'}
              onChange={handleSelectChange}
              aria-label={t('localization.selectorLabel')}
              bg="bg.surface"
            >
              <option value="default">{t('localization.defaultOption')}</option>
              {availableLanguages.map((languageCode) => (
                <option key={languageCode} value={languageCode}>
                  {t(`localization.languageNames.${languageCode}`, {
                    defaultValue: languageCode.toUpperCase(),
                  })}
                </option>
              ))}
            </Select>
          </FormControl>
        )}
      </Stack>

      <Stack spacing={2}>
        <Text as="h1" fontSize="2xl" fontWeight="700">
          {request.title}
        </Text>
        <Text color="text.subtle" fontSize="md">
          {t(subtitleKey)}
        </Text>
      </Stack>

      <MediaInfo request={request} />
    </Stack>
  );
}
