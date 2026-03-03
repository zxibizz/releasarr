import { Stack, Text } from '@chakra-ui/react';

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
    <Stack spacing={4} w="100%">
      {hasExistingReleases && (
        <Stack spacing={1}>
          <Text as="h2" fontSize="lg" fontWeight="700">
            📦 Releases
          </Text>
          <Text color="text.subtle" fontSize="sm">
            Releases linked to this request
          </Text>
        </Stack>
      )}

      <ReleasesList
        requestId={request.id}
        onViewFiles={onViewFiles}
        onReleasesLoaded={onReleasesLoaded}
      />
    </Stack>
  );
}
