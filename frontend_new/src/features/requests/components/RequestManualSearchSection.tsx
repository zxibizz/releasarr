import { Box, Collapse } from '@chakra-ui/react';
import type { RefObject } from 'react';

import { ReleaseSearch } from '@/features/requests/ReleaseSearch';
import type { MediaRequest } from '@/types';

interface RequestManualSearchSectionProps {
  request: MediaRequest;
  shouldShowSearch: boolean;
  manualSearchSectionRef: RefObject<HTMLDivElement | null>;
  isShaking: boolean;
  shakeAnimation: string;
  manualSearchPrefill: string | null;
  manualSearchFocusToken: number;
  onDownloadQueued: () => Promise<void> | void;
}

export function RequestManualSearchSection({
  request,
  shouldShowSearch,
  manualSearchSectionRef,
  isShaking,
  shakeAnimation,
  manualSearchPrefill,
  manualSearchFocusToken,
  onDownloadQueued,
}: RequestManualSearchSectionProps) {
  return (
    <Collapse in={shouldShowSearch} animateOpacity unmountOnExit style={{ width: '100%' }}>
      <Box
        ref={manualSearchSectionRef}
        w="100%"
        sx={{
          willChange: 'transform',
          animation: isShaking ? `${shakeAnimation}` : undefined,
        }}
      >
        <ReleaseSearch
          requestId={request.id}
          requestTitle={request.title}
          onDownloadQueued={onDownloadQueued}
          prefillQuery={manualSearchPrefill}
          focusTrigger={manualSearchFocusToken}
        />
      </Box>
    </Collapse>
  );
}
