import {
  Alert,
  AlertDescription,
  AlertIcon,
  AlertTitle,
  Box,
  Button,
  Center,
  Heading,
  Spinner,
  Stack,
  Text,
  VStack,
  useToast,
} from "@chakra-ui/react";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useReleasesByRequestQuery } from "../hooks/useReleases";
import { Release, MediaRequest } from "../types";
import {
  fetchRequest,
  deleteRelease as deleteReleaseApi,
  pauseRelease as pauseReleaseApi,
  resumeRelease as resumeReleaseApi,
} from "../services/api";
import { sortReleasesByStatus } from "../utils/releaseHelpers";
import ReleaseCard from "./ReleaseCard";

interface ReleasesListProps {
  requestId: string;
  onPauseRelease?: (id: string) => void;
  onResumeRelease?: (id: string) => void;
  onDeleteRelease?: (id: string) => void;
  onViewFiles?: (release: Release) => void;
  compact?: boolean;
  onReleasesLoaded?: (releases: Release[]) => void;
  refreshToken?: number;
  hideEmptyState?: boolean;
}

type RequestSummary = Pick<MediaRequest, "id" | "title" | "year" | "type">;

const ReleasesList: React.FC<ReleasesListProps> = ({
  requestId,
  onPauseRelease,
  onResumeRelease,
  onDeleteRelease,
  onViewFiles,
  compact = false,
  onReleasesLoaded,
  refreshToken,
  hideEmptyState = false,
}) => {
  const {
    data,
    isLoading,
    isFetching,
    error,
    refetch,
  } = useReleasesByRequestQuery(requestId, {
    enabled: Boolean(requestId),
  });
  const releases = useMemo(() => data ?? [], [data]);
  const [requestSummaries, setRequestSummaries] = useState<
    Record<string, RequestSummary>
  >({});
  const toast = useToast();

  useEffect(() => {
    if (!requestId) {
      return;
    }
    if (refreshToken === undefined) {
      return;
    }
    refetch();
  }, [refetch, refreshToken, requestId]);

  const releasesToRender = useMemo(() => sortReleasesByStatus(releases), [releases]);

  useEffect(() => {
    if (isLoading || isFetching) {
      return;
    }

    onReleasesLoaded?.(releases);
  }, [isFetching, isLoading, releases, onReleasesLoaded]);

  useEffect(() => {
    if (isLoading || isFetching || releases.length === 0) {
      return;
    }

    const uniqueIds = new Set<string>();
    releases.forEach((release) => {
      release.request_ids.forEach((id) => {
        if (id && id !== requestId) {
          uniqueIds.add(id);
        }
      });
    });

    const missingIds = Array.from(uniqueIds).filter(
      (id) => !requestSummaries[id]
    );

    if (missingIds.length === 0) {
      return;
    }

    let cancelled = false;

    const loadSummaries = async () => {
      const results = await Promise.all(
        missingIds.map(async (id) => {
          try {
            const request = await fetchRequest(id);
            return {
              id: request.id,
              title: request.title,
              year: request.year,
              type: request.type,
            } as RequestSummary;
          } catch (fetchError) {
            console.error("Failed to fetch related request", id, fetchError);
            return null;
          }
        })
      );

      if (cancelled) {
        return;
      }

      setRequestSummaries((prev) => {
        const next = { ...prev };
        results.forEach((summary) => {
          if (summary) {
            next[summary.id] = summary;
          }
        });
        return next;
      });
    };

    loadSummaries();

    return () => {
      cancelled = true;
    };
  }, [isFetching, isLoading, releases, requestId, requestSummaries]);

  const handleDeleteRelease = useCallback(
    async (id: string) => {
      try {
        await deleteReleaseApi(id);
        toast({
          title: "Release deleted",
          status: "success",
          duration: 3000,
          isClosable: true,
        });
        onDeleteRelease?.(id);
        await refetch();
      } catch (deleteError) {
        console.error("Failed to delete release", deleteError);
        toast({
          title: "Failed to delete release",
          status: "error",
          duration: 4000,
          isClosable: true,
        });
        throw deleteError;
      }
    },
    [onDeleteRelease, refetch, toast]
  );

  const handlePauseRelease = useCallback(
    async (id: string) => {
      try {
        await pauseReleaseApi(id);
        toast({
          title: "Release paused",
          status: "success",
          duration: 3000,
          isClosable: true,
        });
        onPauseRelease?.(id);
        await refetch();
      } catch (pauseError) {
        console.error("Failed to pause release", pauseError);
        toast({
          title: "Failed to pause release",
          status: "error",
          duration: 4000,
          isClosable: true,
        });
        throw pauseError;
      }
    },
    [onPauseRelease, refetch, toast]
  );

  const handleResumeRelease = useCallback(
    async (id: string) => {
      try {
        await resumeReleaseApi(id);
        toast({
          title: "Release resumed",
          status: "success",
          duration: 3000,
          isClosable: true,
        });
        onResumeRelease?.(id);
        await refetch();
      } catch (resumeError) {
        console.error("Failed to resume release", resumeError);
        toast({
          title: "Failed to resume release",
          status: "error",
          duration: 4000,
          isClosable: true,
        });
        throw resumeError;
      }
    },
    [onResumeRelease, refetch, toast]
  );

  const errorMessage =
    error instanceof Error ? error.message : error ? "Failed to load releases" : null;

  const showLoadingState = (isLoading || isFetching) && releases.length === 0;

  if (showLoadingState) {
    return (
      <Center py={10} flexDirection="column" gap={4} color="text.subtle">
        <Spinner size="lg" color="brand.400" />
        <Text>Loading releases...</Text>
      </Center>
    );
  }

  if (errorMessage) {
    return (
      <Alert
        status="error"
        variant="subtle"
        borderRadius="xl"
        p={6}
        flexDirection="column"
        alignItems="flex-start"
        gap={4}
      >
        <AlertIcon />
        <Box>
          <AlertTitle fontSize="lg">Error loading releases</AlertTitle>
          <AlertDescription>{errorMessage}</AlertDescription>
        </Box>
        <Button
          variant="outline"
          colorScheme="blue"
          size="sm"
          onClick={() => refetch()}
        >
          Try Again
        </Button>
      </Alert>
    );
  }

  if (releases.length === 0) {
    if (hideEmptyState) {
      return null;
    }
    return (
      <VStack
        spacing={3}
        py={16}
        bg="bg.subtle"
        borderRadius="xl"
        borderWidth="1px"
        borderColor="border.muted"
      >
        <Text fontSize="4xl">📦</Text>
        <Heading size="md">No releases found</Heading>
        <Text color="text.subtle" fontSize="sm">
          No releases have been added for this request yet.
        </Text>
      </VStack>
    );
  }

  return (
    <Stack spacing={6}>
      <Stack spacing={compact ? 3 : 4}>
        {releasesToRender.map((release) => (
          <ReleaseCard
            key={release.id}
            release={release}
            onPause={handlePauseRelease}
            onResume={handleResumeRelease}
            onDelete={handleDeleteRelease}
            onViewFiles={onViewFiles}
            compact={compact}
            currentRequestId={requestId}
            requestSummaries={requestSummaries}
          />
        ))}
      </Stack>
    </Stack>
  );
};

export default ReleasesList;

