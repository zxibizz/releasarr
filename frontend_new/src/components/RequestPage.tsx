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
import { useQueryClient } from "@tanstack/react-query";
import { Link as RouterLink, useParams } from "react-router-dom";
import { useRequestQuery } from "../hooks/useRequests";
import { Release } from "../types";
import { fetchRequestLogs } from "../services/requestLogs";
import { RequestLogEntry } from "../types/logs";
import { MediaInfo } from "./MediaInfo";
import ReleaseFilesModal from "./ReleaseFilesModal";
import { ReleaseSearch } from "./ReleaseSearch";
import ReleasesList from "./ReleasesList";
import { releasesKeys } from "../lib/queryKeys";

const shakeKeyframes = keyframes`
  0%, 100% { transform: translateX(0); }
  20%, 60% { transform: translateX(-6px); }
  40%, 80% { transform: translateX(6px); }
`;

const MIN_SHAKE_INTERVAL_MS = 1200;

type RawRequestLogEntry = Partial<RequestLogEntry> & Record<string, unknown>;

const REQUEST_LOG_LEVELS: RequestLogEntry["level"][] = [
  "info",
  "warning",
  "error",
];

const toMilliseconds = (value: number): number => {
  return value < 1_000_000_000_000 ? value * 1000 : value;
};

const parseNumericTimestamp = (value: unknown): number | null => {
  if (typeof value === "number" && Number.isFinite(value)) {
    return toMilliseconds(value);
  }

  if (typeof value === "string" && value.trim().length > 0) {
    const numeric = Number.parseFloat(value);
    if (Number.isFinite(numeric)) {
      return toMilliseconds(numeric);
    }

    const parsedDate = Date.parse(value);
    if (!Number.isNaN(parsedDate)) {
      return parsedDate;
    }
  }

  return null;
};

const coerceMetadata = (
  value: unknown
): Record<string, string | number | boolean> | undefined => {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    const entries = Object.entries(value).reduce(
      (acc, [key, entryValue]) => {
        if (
          typeof entryValue === "string" ||
          typeof entryValue === "number" ||
          typeof entryValue === "boolean"
        ) {
          acc[key] = entryValue;
        }
        return acc;
      },
      {} as Record<string, string | number | boolean>
    );

    return Object.keys(entries).length > 0 ? entries : undefined;
  }

  return undefined;
};

const normalizeLogEntry = (
  entry: unknown,
  fallbackId: string
): RequestLogEntry => {
  const raw: RawRequestLogEntry =
    entry && typeof entry === "object" && !Array.isArray(entry)
      ? (entry as RawRequestLogEntry)
      : {};

  const occurredAtCandidate =
    raw.occurredAt ??
    raw.occurred_at ??
    raw.timestamp ??
    raw.time ??
    raw.createdAt ??
    raw.created_at;

  const occurredAt =
    parseNumericTimestamp(occurredAtCandidate) ?? Date.now();

  const idCandidate = raw.id ?? raw.logId ?? raw.log_id ?? raw.uuid ?? fallbackId;
  const id = String(idCandidate ?? fallbackId);

  const levelCandidate =
    (raw.level ?? raw.logLevel ?? raw.log_level ?? raw.severity) as
      | string
      | undefined;
  const normalizedLevel = levelCandidate?.toLowerCase().trim();
  const level: RequestLogEntry["level"] = REQUEST_LOG_LEVELS.includes(
    normalizedLevel as RequestLogEntry["level"]
  )
    ? (normalizedLevel as RequestLogEntry["level"])
    : "info";

  const messageValue = raw.message ?? raw.detail ?? raw.description ?? "";
  const message = typeof messageValue === "string" ? messageValue : String(messageValue ?? "");

  const timestampValue =
    typeof raw.timestamp === "string"
      ? raw.timestamp
      : typeof raw.occurred_at === "string"
        ? raw.occurred_at
        : undefined;

  const timestamp =
    (timestampValue && timestampValue.trim().length > 0
      ? timestampValue
      : new Date(occurredAt).toLocaleString()) ?? "";

  const sourceValue = raw.source ?? raw.component ?? raw.origin;
  const source = typeof sourceValue === "string" ? sourceValue : undefined;

  const stackTraceValue = raw.stackTrace ?? raw.stack_trace ?? raw.stack;
  const stackTrace =
    typeof stackTraceValue === "string" && stackTraceValue.trim().length > 0
      ? stackTraceValue
      : undefined;

  return {
    id,
    occurredAt,
    timestamp,
    level,
    message,
    source,
    metadata: coerceMetadata(raw.metadata ?? raw.meta ?? raw.context),
    stackTrace,
  };
};

const normalizeRequestLogs = (logs: unknown[]): RequestLogEntry[] => {
  const normalizationSeed = Date.now();
  return logs.map((log, index) =>
    normalizeLogEntry(log, `log-${normalizationSeed}-${index}`)
  );
};

export const RequestPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const {
    data: request,
    isLoading,
    isFetching,
    error: requestError,
    refetch: refetchRequest,
  } = useRequestQuery(id, {
    enabled: Boolean(id),
  });
  const [selectedRelease, setSelectedRelease] = useState<Release | null>(null);
  const [hasExistingReleases, setHasExistingReleases] = useState(false);
  const [manualSearchTriggered, setManualSearchTriggered] = useState(false);
  const [shakeSignal, setShakeSignal] = useState(0);
  const [isShaking, setIsShaking] = useState(false);
  const [manualSearchPrefill, setManualSearchPrefill] = useState<string | null>(
    null
  );
  const [manualSearchFocusToken, setManualSearchFocusToken] = useState(0);
  const [requestLogs, setRequestLogs] = useState<RequestLogEntry[]>([]);
  const [logsLoading, setLogsLoading] = useState(false);
  const [logsError, setLogsError] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const refreshToastIdRef = useRef<string | number | undefined>(undefined);
  const manualSearchSectionRef = useRef<HTMLDivElement | null>(null);
  const lastShakeAtRef = useRef(0);
  const previousShouldShowSearch = useRef(false);

  const filesModal = useDisclosure();
  const {
    isOpen: isLogsOpen,
    onOpen: openLogs,
    onClose: closeLogs,
  } = useDisclosure();
  const toast = useToast();

  const showLoadingState = (isLoading || isFetching) && !request;
  const requestErrorMessage =
    requestError instanceof Error
      ? requestError.message
      : requestError
        ? "Failed to load request"
        : null;

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

  const invalidateReleases = useCallback(async () => {
    if (!id) {
      return;
    }

    await Promise.all([
      queryClient.invalidateQueries({ queryKey: releasesKeys.byRequest(id), exact: true }),
      queryClient.invalidateQueries({ queryKey: releasesKeys.list({ requestId: id }) }),
      queryClient.invalidateQueries({ queryKey: releasesKeys.all }),
    ]);
  }, [id, queryClient]);

  const focusManualSearch = useCallback(() => {
    setManualSearchFocusToken((token) => token + 1);
    requestAnimationFrame(() => {
      manualSearchSectionRef.current?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    });
  }, []);

  useEffect(() => {
    setHasExistingReleases(false);
    setManualSearchTriggered(false);
    setManualSearchPrefill(null);
    setManualSearchFocusToken(0);
    setRequestLogs([]);
    setLogsError(null);
    setLogsLoading(false);
    lastShakeAtRef.current = 0;
  }, [request?.id]);


  const handleViewFiles = (release: Release) => {
    setSelectedRelease(release);
    filesModal.onOpen();
  };

  const closeModal = () => {
    filesModal.onClose();
    setSelectedRelease(null);
  };

  const handleReleasesLoaded = useCallback(
    (loadedReleases: Release[]) => {
      const hasReleases = loadedReleases.length > 0;
      setHasExistingReleases(hasReleases);

      if (!hasReleases) {
        setManualSearchTriggered(false);
        const normalizedTitle = request?.title?.trim() ?? "";
        setManualSearchPrefill((prev) => {
          if (prev && prev.trim().length > 0) {
            return prev;
          }
          return normalizedTitle || null;
        });
      } else {
        setManualSearchPrefill(null);
      }
    },
    [request?.title]
  );

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
    focusManualSearch();

    if (searchAlreadyVisible) {
      const now = Date.now();
      if (now - lastShakeAtRef.current >= MIN_SHAKE_INTERVAL_MS) {
        lastShakeAtRef.current = now;
        setShakeSignal((signal) => signal + 1);
      }
    } else {
      lastShakeAtRef.current = Date.now();
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
    focusManualSearch,
    hasExistingReleases,
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
      await invalidateReleases();

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
  }, [id, invalidateReleases, isRefreshing, refetchRequest, toast, updateRefreshToast]);

  const loadLogs = useCallback(async () => {
    if (!request) {
      return;
    }
    setLogsLoading(true);
    setLogsError(null);
    try {
      const logs = await fetchRequestLogs(request.id);
      setRequestLogs(normalizeRequestLogs(logs));
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

  useEffect(() => {
    if (shouldShowSearch && !previousShouldShowSearch.current) {
      focusManualSearch();
    }
    previousShouldShowSearch.current = shouldShowSearch;
  }, [focusManualSearch, shouldShowSearch]);

  if (showLoadingState) {
    return (
      <Center py={16} flexDirection="column" gap={4} color="text.subtle">
        <Spinner size="lg" color="brand.400" />
        <Text>Loading request...</Text>
      </Center>
    );
  }

  if (requestErrorMessage || !request) {
    return (
      <Card p={8} maxW="lg" mx="auto">
        <Stack spacing={4} align="center">
          <Text fontSize="3xl">❌</Text>
          <Heading size="md">Request not found</Heading>
          <Text color="text.subtle" textAlign="center">
            {requestErrorMessage || "The requested media could not be found."}
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

      <Card p={{ base: 5, md: 6 }} display={hasExistingReleases ? "block" : "none"}>
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
            hideEmptyState
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
          ref={manualSearchSectionRef}
          w="100%"
          sx={{
            willChange: "transform",
            animation: isShaking ? `${shakeKeyframes} 0.45s cubic-bezier(0.36, 0.07, 0.19, 0.97)` : undefined,
          }}
        >
          <ReleaseSearch
            requestId={request.id}
            requestTitle={request.title}
            onDownloadQueued={() => {
              void invalidateReleases();
            }}
            prefillQuery={manualSearchPrefill}
            focusTrigger={manualSearchFocusToken}
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
