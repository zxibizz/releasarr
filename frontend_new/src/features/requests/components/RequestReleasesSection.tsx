import { Card, Stack, Text } from '@chakra-ui/react';

import ReleasesList from '@/features/requests/ReleasesList';
import type { MediaRequest, Release } from '@/types';

interface RequestReleasesSectionProps {
  request: MediaRequest;
  hasExistingReleases: boolean;
  onReleasesLoaded: (releases: Release[]) => void;
  onViewFiles: (release: Release) => void;
}

export function RequestReleasesSection({
  request,
  hasExistingReleases,
  onReleasesLoaded,
  onViewFiles,
}: RequestReleasesSectionProps) {
  return (
    <Card p={{ base: 5, md: 6 }} display={hasExistingReleases ? 'block' : 'none'}>
      <Stack spacing={4}>
        <Stack spacing={1}>
          <Text as="h2" fontSize="lg" fontWeight="700">
            📦 Releases
          </Text>
          <Text color="text.subtle" fontSize="sm">
            Releases linked to this request
          </Text>
        </Stack>

        <ReleasesList
          requestId={request.id}
          onViewFiles={onViewFiles}
          onReleasesLoaded={onReleasesLoaded}
          hideEmptyState
        />
      </Stack>
    </Card>
  );
}
