import { Button, Stack, Text } from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';
import { Link as RouterLink } from 'react-router-dom';

import { MediaInfo } from '@/features/requests/MediaInfo';
import type { MediaRequest } from '@/types';

interface RequestHeaderProps {
  request: MediaRequest;
}

export function RequestHeader({ request }: RequestHeaderProps) {
  const { t } = useTranslation();
  const subtitleKey =
    request.type === 'movie' ? 'requestHeader.subtitle.movie' : 'requestHeader.subtitle.series';

  return (
    <Stack spacing={8}>
      <Button as={RouterLink} to="/" variant="outline" colorScheme="blue" width="fit-content">
        {t('common.backToRequests')}
      </Button>

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
