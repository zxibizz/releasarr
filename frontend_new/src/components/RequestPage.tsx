import {
  Alert,
  AlertDescription,
  AlertIcon,
  Box,
  Button,
  Card,
  Center,
  Collapse,
  Heading,
  SimpleGrid,
  Spinner,
  Stack,
  StackDivider,
  Text,
  Badge,
  Flex,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalOverlay,
  useDisclosure,
  useToast,
} from "@chakra-ui/react";
import type { UseToastOptions } from "@chakra-ui/react";
import { keyframes } from "@emotion/react";
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link as RouterLink, useParams } from "react-router-dom";
import { useRequest } from "../hooks/useRequests";
import { Release } from "../types";
import { fetchRequestLogs } from "../services/requestLogs";
import { RequestLogEntry } from "../types/logs";
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
  const { request, loading, error, refetch: refetchRequest } = useRequest(id || "");
  const [selectedRelease, setSelectedRelease] = useState<Release | null>(null);
  const [hasExistingReleases, setHasExistingReleases] = useState(false);
  const [manualSearchTriggered, setManualSearchTriggered] = useState(false);
  const [shakeSignal, setShakeSignal] = useState(0);
  const [isShaking, setIsShaking] = useState(false);
  const [releasesRefreshToken, setReleasesRefreshToken] = useState(0);
  const [manualSearchPrefill, setManualSearchPrefill] = useState<string | null>(
    null
  );
  const [requestLogs, setRequestLogs] = useState<RequestLogEntry[]>([]);
  const [logsLoading, setLogsLoading] = useState(false);
  const [logsError, setLogsError] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const refreshToastIdRef = useRef<string | number | undefined>(undefined);

  const filesModal = useDisclosure();
  const {
    isOpen: isLogsOpen,
    onOpen: openLogs,
    onClose: closeLogs,
  } = useDisclosure();
  const toast = useToast();

  const updateRefreshToast = useCallback(
    (options: UseToastOptions) => {
      const toastId = refreshToastIdRef.current;
      if (toastId && toast.isActive(toastId)) {
        toast.update(toastId, options);
      } else {
        refreshToastIdRef.current = toast(options);
      }
    },
    [toast]
  );

  useEffect(() => {
    setReleasesRefreshToken(0);
    setHasExistingReleases(false);
    setManualSearchTriggered(false);
    setManualSearchPrefill(null);
    setRequestLogs([]);
    setLogsError(null);
    setLogsLoading(false);
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
    if (!request || !request.title) {
      toast({
        title: "Manual search unavailable",
        description: "Missing request details; cannot build search query.",
        status: "warning",
        duration: 4000,
        isClosable: true,
      });
      return;
    }

    const searchAlreadyVisible = !hasExistingReleases || manualSearchTriggered;
    setManualSearchTriggered(true);
    if (searchAlreadyVisible) {
      setShakeSignal((signal) => signal + 1);
    }

    const normalizedQuery = request.title.trim();
    if (!normalizedQuery) {
      toast({
        title: "Manual search unavailable",
        description: "Request title is empty; please update the request first.",
        status: "warning",
        duration: 4000,
        isClosable: true,
      });
      return;
    }

    setManualSearchPrefill(normalizedQuery);
  }, [
    hasExistingReleases,
    id,
    manualSearchTriggered,
    request,
    toast,
  ]);

  const handleRefreshStatus = useCallback(async () => {
    if (!id || isRefreshing) {
      return;
    }

    setIsRefreshing(true);

    const loadingToastId = toast({
      id: `refresh-request-${id}`,
      title: "Refreshing status",
      description: "Checking for the latest updates...",
      status: "info",
      duration: null,
      isClosable: false,
    });
    refreshToastIdRef.current = loadingToastId;

    try {
      await refetchRequest();
      setReleasesRefreshToken((token) => token + 1);

      updateRefreshToast({
        title: "Status refreshed",
        description: "Request details and releases are up to date.",
        status: "success",
        duration: 2500,
        isClosable: true,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to refresh request";
      updateRefreshToast({
        title: "Refresh failed",
        description: message,
        status: "error",
        duration: 4000,
        isClosable: true,
      });
    } finally {
      setIsRefreshing(false);
      refreshToastIdRef.current = undefined;
    }
  }, [id, isRefreshing, refetchRequest, toast, updateRefreshToast]);

  const loadLogs = useCallback(async () => {
    if (!request) {
      return;
    }
    setLogsLoading(true);
    setLogsError(null);
    try {
      const logs = await fetchRequestLogs(request.id);
      setRequestLogs(logs);
    } catch (err) {
      setLogsError(
        err instanceof Error ? err.message : "Failed to load logs"
      );
    } finally {
      setLogsLoading(false);
    }
  }, [request]);

  const handleViewLogs = useCallback(() => {
    loadLogs();
    openLogs();
  }, [loadLogs, openLogs]);

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
        onClick: handleRefreshStatus,
        isLoading: isRefreshing,
        isDisabled: isRefreshing,
        loadingText: "Refreshing...",
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
        onClick: handleViewLogs,
      },
    ],
    [
      handleManualSearch,
      handleRefreshStatus,
      handleViewLogs,
      isRefreshing,
    ]
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
            prefillQuery={manualSearchPrefill}
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
                  void action.onClick?.();
                }}
                isDisabled={action.isDisabled}
                isLoading={action.isLoading}
                loadingText={action.loadingText}
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

      <RequestLogsModal
        isOpen={isLogsOpen}
        onClose={closeLogs}
        logs={requestLogs}
        requestTitle={request.title}
        isLoading={logsLoading}
        error={logsError}
      />
    </Stack>
  );
};

interface RequestLogsModalProps {
  isOpen: boolean;
  onClose: () => void;
  logs: RequestLogEntry[];
  requestTitle: string;
  isLoading: boolean;
  error: string | null;
}

const levelColorScheme: Record<RequestLogEntry["level"], string> = {
  info: "blue",
  warning: "yellow",
  error: "red",
};

const RequestLogsModal: React.FC<RequestLogsModalProps> = ({
  isOpen,
  onClose,
  logs,
  requestTitle,
  isLoading,
  error,
}) => {
  const sortedLogs = useMemo(
    () => [...logs].sort((a, b) => b.occurredAt - a.occurredAt),
    [logs]
  );
  const [expandedStacks, setExpandedStacks] = useState<Record<string, boolean>>(
    {}
  );

  useEffect(() => {
    setExpandedStacks({});
  }, [sortedLogs]);

  const toggleStackTrace = useCallback((logId: string) => {
    setExpandedStacks((prev) => ({
      ...prev,
      [logId]: !prev[logId],
    }));
  }, []);

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="xl" scrollBehavior="inside">
      <ModalOverlay />
      <ModalContent maxW="4xl" w="full">
        <ModalHeader>Logs for {requestTitle}</ModalHeader>
        <ModalCloseButton />
        <ModalBody maxH="60vh" overflowY="auto">
          {isLoading ? (
            <Center py={8}>
              <Stack spacing={3} align="center">
                <Spinner color="brand.400" />
                <Text color="text.subtle" fontSize="sm">
                  Loading logs...
                </Text>
              </Stack>
            </Center>
          ) : error ? (
            <Alert status="error" variant="left-accent" borderRadius="md">
              <AlertIcon />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          ) : sortedLogs.length === 0 ? (
            <Text color="text.subtle">No logs available for this request.</Text>
          ) : (
            <Stack spacing={4} divider={<StackDivider borderColor="border.muted" />}>
              {sortedLogs.map((log) => (
                <Stack key={log.id} spacing={3} fontSize="sm">
                  <Flex justify="space-between" align="center" gap={4} wrap="wrap">
                    <Text color="text.subtle">{log.timestamp}</Text>
                    <Flex align="center" gap={2} wrap="wrap">
                      {log.source && (
                        <Badge colorScheme="gray" variant="subtle">
                          {log.source}
                        </Badge>
                      )}
                      <Badge colorScheme={levelColorScheme[log.level]}>
                        {log.level.toUpperCase()}
                      </Badge>
                    </Flex>
                  </Flex>
                  <Text fontWeight="600" fontSize="md">
                    {log.message}
                  </Text>
                  {log.metadata && (
                    <Stack spacing={2}>
                      <Text fontWeight="600" fontSize="xs" color="text.subtle">
                        Context
                      </Text>
                      <SimpleGrid columns={{ base: 1, sm: 2 }} spacing={2} fontSize="xs">
                        {Object.entries(log.metadata).map(([key, value]) => (
                          <Flex
                            key={key}
                            justify="space-between"
                            gap={3}
                            p={2}
                            borderWidth="1px"
                            borderRadius="md"
                            bg="bg.muted"
                          >
                            <Text fontWeight="600">{key}</Text>
                            <Text color="text.subtle" textAlign="right">
                              {String(value)}
                            </Text>
                          </Flex>
                        ))}
                      </SimpleGrid>
                    </Stack>
                  )}
                  {log.stackTrace && (
                    <Stack spacing={2}>
                      <Button
                        variant="link"
                        size="xs"
                        colorScheme="red"
                        width="fit-content"
                        onClick={() => toggleStackTrace(log.id)}
                      >
                        {expandedStacks[log.id] ? "Hide stack trace" : "View stack trace"}
                      </Button>
                      {expandedStacks[log.id] && (
                        <Box
                          as="pre"
                          fontSize="xs"
                          fontFamily="mono"
                          whiteSpace="pre-wrap"
                          p={3}
                          borderWidth="1px"
                          borderRadius="md"
                          bg="bg.subtle"
                          color="text.subtle"
                        >
                          {log.stackTrace}
                        </Box>
                      )}
                    </Stack>
                  )}
                </Stack>
              ))}
            </Stack>
          )}
        </ModalBody>
        <ModalFooter>
          <Button onClick={onClose}>Close</Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};
