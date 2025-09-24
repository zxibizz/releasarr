import {
  Box,
  Button,
  Card,
  Center,
  Collapse,
  Heading,
  SimpleGrid,
  Spinner,
  Stack,
  Text,
  useDisclosure,
} from "@chakra-ui/react";
import { keyframes } from "@emotion/react";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Link as RouterLink, useParams } from "react-router-dom";
import { useRequest } from "../hooks/useRequests";
import { Release } from "../types";
import { MediaInfo } from "./MediaInfo";
import ReleaseFilesModal from "./ReleaseFilesModal";
import { ReleaseSearch } from "./ReleaseSearch";
import ReleasesList from "./ReleasesList";

const shakeKeyframes = keyframes`
  0%, 100% { transform: translateX(0); }
  20%, 60% { transform: translateX(-6px); }
  40%, 80% { transform: translateX(6px); }
`;

export const RequestPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { request, loading, error } = useRequest(id || "");
  const [selectedRelease, setSelectedRelease] = useState<Release | null>(null);
  const [hasExistingReleases, setHasExistingReleases] = useState(false);
  const [manualSearchTriggered, setManualSearchTriggered] = useState(false);
  const [shakeSignal, setShakeSignal] = useState(0);
  const [isShaking, setIsShaking] = useState(false);
  const [releasesRefreshToken, setReleasesRefreshToken] = useState(0);

  const filesModal = useDisclosure();

  useEffect(() => {
    setReleasesRefreshToken(0);
    setHasExistingReleases(false);
    setManualSearchTriggered(false);
  }, [request?.id]);

  const handleViewFiles = (release: Release) => {
    setSelectedRelease(release);
    filesModal.onOpen();
  };

  const closeModal = () => {
    filesModal.onClose();
    setSelectedRelease(null);
  };

  const handleReleasesLoaded = useCallback((loadedReleases: Release[]) => {
    const hasReleases = loadedReleases.length > 0;
    setHasExistingReleases(hasReleases);
    if (!hasReleases) {
      setManualSearchTriggered(false);
    }
  }, []);

  const handleManualSearch = useCallback(() => {
    const searchAlreadyVisible = !hasExistingReleases || manualSearchTriggered;
    setManualSearchTriggered(true);
    if (searchAlreadyVisible) {
      setShakeSignal((signal) => signal + 1);
    }
  }, [hasExistingReleases, manualSearchTriggered]);

  useEffect(() => {
    if (shakeSignal === 0) {
      return;
    }
    setIsShaking(true);
    const timeout = window.setTimeout(() => setIsShaking(false), 500);
    return () => window.clearTimeout(timeout);
  }, [shakeSignal]);

  const actionCards = useMemo(
    () => [
      {
        title: "Refresh Status",
        description: "Check for updates on this request",
        icon: "🔄",
        message: "Refresh functionality would be implemented here",
      },
      {
        title: "Manual Search",
        description: "Trigger a manual search for releases",
        icon: "🔍",
        onClick: handleManualSearch,
      },
      {
        title: "View Logs",
        description: "Check processing logs for this request",
        icon: "📋",
        message: "View logs functionality would be implemented here",
      },
    ],
    [handleManualSearch]
  );

  const shouldShowSearch = !hasExistingReleases || manualSearchTriggered;

  if (loading) {
    return (
      <Center py={16} flexDirection="column" gap={4} color="text.subtle">
        <Spinner size="lg" color="brand.400" />
        <Text>Loading request...</Text>
      </Center>
    );
  }

  if (error || !request) {
    return (
      <Card p={8} maxW="lg" mx="auto">
        <Stack spacing={4} align="center">
          <Text fontSize="3xl">❌</Text>
          <Heading size="md">Request not found</Heading>
          <Text color="text.subtle" textAlign="center">
            {error || "The requested media could not be found."}
          </Text>
          <Button as={RouterLink} to="/" colorScheme="blue">
            ← Back to Requests
          </Button>
        </Stack>
      </Card>
    );
  }

  return (
    <Stack spacing={8} maxW="6xl" mx="auto">
      <Button
        as={RouterLink}
        to="/"
        variant="outline"
        colorScheme="blue"
        width="fit-content"
      >
        ← Back to Requests
      </Button>

      <Stack spacing={2}>
        <Heading size="2xl">{request.title}</Heading>
        <Text color="text.subtle" fontSize="md">
          {request.type === "movie" ? "Movie" : "TV Series"} Request Details
        </Text>
      </Stack>

      <MediaInfo request={request} />

      <Card p={{ base: 5, md: 6 }}>
        <Stack spacing={4}>
          <Stack spacing={1}>
            <Heading size="md">📦 Releases</Heading>
            <Text color="text.subtle" fontSize="sm">
              Releases linked to this request
            </Text>
          </Stack>

          <ReleasesList
            requestId={request.id}
            onViewFiles={handleViewFiles}
            onReleasesLoaded={handleReleasesLoaded}
            refreshToken={releasesRefreshToken}
          />
        </Stack>
      </Card>

      <Collapse
        in={shouldShowSearch}
        animateOpacity
        unmountOnExit
        style={{ width: "100%" }}
      >
        <Box
          w="100%"
          sx={{
            willChange: "transform",
            animation: isShaking ? `${shakeKeyframes} 0.45s cubic-bezier(0.36, 0.07, 0.19, 0.97)` : undefined,
          }}
        >
          <ReleaseSearch
            requestId={request.id}
            requestTitle={request.title}
            onDownloadQueued={() =>
              setReleasesRefreshToken((prevToken) => prevToken + 1)
            }
          />
        </Box>
      </Collapse>

      <Card p={{ base: 5, md: 6 }}>
        <Stack spacing={4}>
          <Heading size="md">🔧 Request Actions</Heading>
          <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4}>
            {actionCards.map((action) => (
              <Card
                key={action.title}
                p={4}
                bg="bg.subtle"
                borderWidth="1px"
                borderColor="border.muted"
                as={Button}
                variant="ghost"
                colorScheme="gray"
                textAlign="left"
                height="auto"
                flexDirection="column"
                alignItems="flex-start"
                onClick={() => {
                  if (action.onClick) {
                    action.onClick();
                  } else if (action.message) {
                    alert(action.message);
                  }
                }}
              >
                <Text fontSize="2xl" mb={2}>
                  {action.icon}
                </Text>
                <Text fontWeight="600" mb={1}>
                  {action.title}
                </Text>
                <Text fontSize="sm" color="text.subtle">
                  {action.description}
                </Text>
              </Card>
            ))}
          </SimpleGrid>
        </Stack>
      </Card>

      <ReleaseFilesModal
        isOpen={filesModal.isOpen}
        onClose={closeModal}
        release={selectedRelease}
        currentRequest={request}
      />
    </Stack>
  );
};
