import { Button, Stack, Text } from '@chakra-ui/react';
import { Link as RouterLink } from 'react-router-dom';

import { MediaInfo } from '@/features/requests/MediaInfo';
import type { MediaRequest } from '@/types';

interface RequestHeaderProps {
  request: MediaRequest;
}

export function RequestHeader({ request }: RequestHeaderProps) {
  return (
    <Stack spacing={8} maxW="6xl" mx="auto">
      <Button as={RouterLink} to="/" variant="outline" colorScheme="blue" width="fit-content">
        ← Back to Requests
      </Button>

      <Stack spacing={2}>
        <Text as="h1" fontSize="2xl" fontWeight="700">
          {request.title}
        </Text>
        <Text color="text.subtle" fontSize="md">
          {request.type === 'movie' ? 'Movie' : 'TV Series'} Request Details
        </Text>
      </Stack>

      <MediaInfo request={request} />
    </Stack>
  );
}
