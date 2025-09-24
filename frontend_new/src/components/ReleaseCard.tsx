import { ChevronDownIcon, ChevronUpIcon, DeleteIcon } from "@chakra-ui/icons";
import {
  AlertDialog,
  AlertDialogBody,
  AlertDialogContent,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogOverlay,
  Badge,
  Button,
  Card,
  Flex,
  Grid,
  GridItem,
  IconButton,
  Progress,
  Stack,
  Tag,
  Text,
  Wrap,
  WrapItem,
} from "@chakra-ui/react";
import React, { useMemo, useRef, useState } from "react";
import { MediaRequest, Release } from "../types";
import {
  calculateETA,
  calculateReleaseProgress,
  formatFileSize,
  formatProgress,
  formatRatio,
  formatSpeed,
  getReleaseHealthScore,
  getStatusIcon,
  groupFilesByType,
  isReleaseActive,
  isReleaseComplete,
} from "../utils/releaseHelpers";

interface ReleaseRequestSummary {
  id: string;
  title: string;
  year?: number;
  type?: MediaRequest["type"];
}

interface ReleaseCardProps {
  release: Release;
  onPause?: (id: string) => Promise<void> | void;
  onResume?: (id: string) => Promise<void> | void;
  onDelete?: (id: string) => Promise<void> | void;
  onViewFiles?: (release: Release) => void;
  showActions?: boolean;
  compact?: boolean;
  currentRequestId?: string;
  requestSummaries?: Record<string, ReleaseRequestSummary>;
}

const statusColorScheme: Record<Release["status"], string> = {
  pending: "yellow",
  downloading: "blue",
  seeding: "purple",
  completed: "green",
  failed: "red",
};

const getHealthColor = (score: number) => {
  if (score > 70) return "green.300";
  if (score > 40) return "yellow.300";
  return "red.300";
};

const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

const ensureFiniteNumber = (value: unknown, fallback = 0) => {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }

  if (typeof value === "string") {
    const parsed = Number.parseFloat(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }

  return fallback;
};

const clampPercentage = (value: number) => {
  if (!Number.isFinite(value)) {
    return 0;
  }

  if (value < 0) {
    return 0;
  }

  if (value > 100) {
    return 100;
  }

  return value;
};

const sanitizeRelease = (release: Release): Release => {
  const size = Math.max(0, ensureFiniteNumber(release.size));
  const progress = clampPercentage(ensureFiniteNumber(release.progress));
  const downloadSpeed = Math.max(0, ensureFiniteNumber(release.download_speed));
  const uploadSpeed = Math.max(0, ensureFiniteNumber(release.upload_speed));
  const seeders = Math.max(0, ensureFiniteNumber(release.seeders));
  const leechers = Math.max(0, ensureFiniteNumber(release.leechers));
  const ratio = Math.max(0, ensureFiniteNumber(release.ratio));

  return {
    ...release,
    files: Array.isArray(release.files) ? release.files : [],
    request_ids: Array.isArray(release.request_ids)
      ? release.request_ids.filter(
          (id): id is string => typeof id === "string" && id.trim().length > 0
        )
      : [],
    status: (release.status ?? "pending") as Release["status"],
    size,
    progress,
    download_speed: downloadSpeed,
    upload_speed: uploadSpeed,
    seeders,
    leechers,
    ratio,
  };
};

const ReleaseCard: React.FC<ReleaseCardProps> = ({
  release: releaseProp,
  onPause,
  onResume,
  onDelete,
  onViewFiles,
  showActions = true,
  compact = false,
  currentRequestId,
  requestSummaries,
}) => {
  const release = useMemo(() => sanitizeRelease(releaseProp), [releaseProp]);
  const [showDetails, setShowDetails] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isDeleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const cancelRef = useRef<HTMLButtonElement | null>(null);

  const progress = calculateReleaseProgress(release);
  const isActive = isReleaseActive(release);
  const isComplete = isReleaseComplete(release);
  const healthScore = getReleaseHealthScore(release);
  const downloadedBytes = Math.min(
    release.size,
    Math.max(0, Math.round((progress / 100) * release.size))
  );
  const downloadedLabel = `${formatFileSize(
    downloadedBytes
  )} / ${formatFileSize(release.size)}`;
  const eta =
    release.status === "downloading" && release.download_speed > 0
      ? calculateETA(release.size, downloadedBytes, release.download_speed)
      : null;
  const { video, subtitle, other } = groupFilesByType(release.files);
  const relatedRequests = useMemo(() => {
    const ids = Array.from(
      new Set(
        (release.request_ids || []).filter((id) =>
          currentRequestId ? id !== currentRequestId : Boolean(id)
        )
      )
    );

    return ids.map((id) => {
      const summary = requestSummaries?.[id];
      return {
        id,
        title: summary?.title ?? id,
        year: summary?.year,
        type: summary?.type,
      };
    });
  }, [release.request_ids, currentRequestId, requestSummaries]);

  const showRelatedRequests = relatedRequests.length > 0;

  const handleAction = async (action: () => Promise<void> | void) => {
    setIsLoading(true);
    try {
      await action();
    } catch (error) {
      console.error("Action failed:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const confirmDelete = () => {
    if (!onDelete) {
      return;
    }

    handleAction(async () => {
      await onDelete(release.id);
      setDeleteDialogOpen(false);
    });
  };

  const deleteDialog = onDelete ? (
    <AlertDialog
      isOpen={isDeleteDialogOpen}
      leastDestructiveRef={cancelRef}
      onClose={() => setDeleteDialogOpen(false)}
    >
      <AlertDialogOverlay>
        <AlertDialogContent>
          <AlertDialogHeader fontSize="lg" fontWeight="bold">
            Delete release
          </AlertDialogHeader>
          <AlertDialogBody>
            This will remove the release and its file mappings from the request.
            Are you sure you want to continue?
          </AlertDialogBody>
          <AlertDialogFooter>
            <Button ref={cancelRef} onClick={() => setDeleteDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              colorScheme="red"
              onClick={confirmDelete}
              ml={3}
              isLoading={isLoading}
            >
              Delete
            </Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialogOverlay>
    </AlertDialog>
  ) : null;

  if (compact) {
    return (
      <>
        <Card
          p={4}
          bg="bg.subtle"
          borderWidth="1px"
          borderColor="border.muted"
          borderRadius="lg"
        >
          <Stack spacing={4}>
            <Flex align="flex-start" justify="space-between" gap={4}>
              <Stack spacing={2} flex={1} minW={0}>
                <Flex align="center" gap={3}>
                  <Text fontSize="xl">{getStatusIcon(release.status)}</Text>
                  <Text fontWeight="700" noOfLines={1}>
                    {release.name}
                  </Text>
                </Flex>
                <Flex gap={3} wrap="wrap" fontSize="xs" color="text.subtle">
                  <Text>{formatFileSize(release.size)}</Text>
                  <Badge
                    colorScheme={statusColorScheme[release.status]}
                    variant="subtle"
                    textTransform="capitalize"
                    px={2}
                    py={1}
                  >
                    {release.status}
                  </Badge>
                  {isActive && <Text>{formatProgress(progress)}</Text>}
                </Flex>
              </Stack>

              {showActions && (
                <Stack direction="row" spacing={2}>
                  <IconButton
                    aria-label="View files"
                    icon={<Text as="span">📁</Text>}
                    variant="ghost"
                    size="sm"
                    onClick={() => onViewFiles?.(release)}
                    isDisabled={isLoading}
                  />
                  <IconButton
                    aria-label="Toggle details"
                    icon={showDetails ? <ChevronUpIcon /> : <ChevronDownIcon />}
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowDetails((prev) => !prev)}
                  />
                  {onDelete && (
                    <IconButton
                      aria-label="Delete release"
                      icon={<DeleteIcon />}
                      variant="ghost"
                      size="sm"
                      colorScheme="red"
                      onClick={() => setDeleteDialogOpen(true)}
                      isDisabled={isLoading}
                    />
                  )}
                </Stack>
              )}
            </Flex>

            {showDetails && (
              <Stack spacing={3} fontSize="xs" color="text.subtle">
                <Grid templateColumns="repeat(2, minmax(0, 1fr))" gap={3}>
                  <GridItem>
                    <Text>Seeders: {release.seeders}</Text>
                  </GridItem>
                  <GridItem>
                    <Text>Leechers: {release.leechers}</Text>
                  </GridItem>
                  <GridItem>
                    <Text>Ratio: {formatRatio(release.ratio)}</Text>
                  </GridItem>
                  <GridItem>
                    <Text>
                      Health:{" "}
                      <Text
                        as="span"
                        fontWeight="600"
                        color={getHealthColor(healthScore)}
                      >
                        {healthScore}%
                      </Text>
                    </Text>
                  </GridItem>
                </Grid>
                {isActive && (
                  <Grid templateColumns="repeat(2, minmax(0, 1fr))" gap={3}>
                    <GridItem>↓ {formatSpeed(release.download_speed)}</GridItem>
                    <GridItem>↑ {formatSpeed(release.upload_speed)}</GridItem>
                  </Grid>
                )}
              </Stack>
            )}
          </Stack>
        </Card>
        {deleteDialog}
      </>
    );
  }

  return (
    <>
      <Card
        p={{ base: 5, md: 6 }}
        bg="bg.subtle"
        borderWidth="1px"
        borderColor="border.muted"
        borderRadius="lg"
      >
        <Stack spacing={6}>
          <Flex
            direction={{ base: "column", md: "row" }}
            align={{ base: "flex-start", md: "flex-start" }}
            justify="space-between"
            gap={6}
          >
            <Stack spacing={2} flex={1} minW={0}>
              <Flex align="center" gap={3} wrap="wrap">
                <Text fontSize="2xl">{getStatusIcon(release.status)}</Text>
                <Text
                  fontWeight="700"
                  fontSize="lg"
                  color="slate.100"
                  noOfLines={2}
                >
                  {release.name}
                </Text>
              </Flex>
              {release.torrent_source && (
                <Text fontSize="sm" color="text.muted">
                  Source: {release.torrent_source}
                </Text>
              )}
            </Stack>

            <Stack
              spacing={2}
              minW={{ base: "auto", md: "200px" }}
              align={{ base: "flex-start", md: "flex-end" }}
            >
              <Badge
                colorScheme={statusColorScheme[release.status]}
                variant="subtle"
                textTransform="capitalize"
                px={3}
                py={1}
              >
                {release.status}
              </Badge>
              <Flex
                gap={2}
                wrap="wrap"
                align="center"
                justify={{ base: "flex-start", md: "flex-end" }}
                fontSize="sm"
                color="text.subtle"
              >
                <Text>{formatFileSize(release.size)}</Text>
                {release.quality && (
                  <Tag colorScheme="blue" borderRadius="full" px={3} py={1}>
                    {release.quality}
                  </Tag>
                )}
              </Flex>
            </Stack>
          </Flex>

          {isActive && (
            <Stack spacing={2}>
              <Flex justify="space-between" fontSize="sm" color="text.subtle">
                <Text>Progress</Text>
                <Text>{formatProgress(progress)}</Text>
              </Flex>
              <Progress
                value={progress}
                colorScheme="blue"
                bg="rgba(71, 85, 105, 0.35)"
                borderRadius="full"
                height="0.5rem"
              />
            </Stack>
          )}

          {!isComplete && (
            <Wrap spacing={2} shouldWrapChildren>
              <Badge variant="solid" colorScheme="blue">
                Downloaded {downloadedLabel}
              </Badge>
              {release.download_speed > 0 && (
                <Badge variant="solid" colorScheme="purple">
                  ↓ {formatSpeed(release.download_speed)}
                </Badge>
              )}
              {eta && (
                <Badge variant="solid" colorScheme="teal">
                  ETA {eta}
                </Badge>
              )}
              {release.upload_speed > 0 && (
                <Badge variant="subtle" colorScheme="green">
                  ↑ {formatSpeed(release.upload_speed)}
                </Badge>
              )}
            </Wrap>
          )}

          {!isComplete && (
            <Flex gap={4} flexWrap="wrap" fontSize="xs" color="text.muted">
              <Text>Seeders: {release.seeders}</Text>
              <Text>Leechers: {release.leechers}</Text>
              <Text>Ratio: {formatRatio(release.ratio)}</Text>
              <Text>Health: {healthScore}%</Text>
            </Flex>
          )}

          {showRelatedRequests && (
            <Stack spacing={2}>
              <Text fontWeight="600" color="text.subtle">
                Related Requests
              </Text>
              <Wrap spacing={2}>
                {relatedRequests.map(({ id, title, year, type }) => {
                  const icon = type === "series" ? "📺" : "🎬";
                  return (
                    <WrapItem key={id}>
                      <Tag
                        colorScheme="blue"
                        variant="subtle"
                        borderRadius="full"
                        px={3}
                        py={1}
                        fontSize="xs"
                        display="inline-flex"
                        alignItems="center"
                        gap={1}
                      >
                        <Text as="span">{icon}</Text>
                        <Text as="span" fontWeight="600">
                          {title}
                        </Text>
                        {year && (
                          <Text as="span" color="text.muted">
                            ({year})
                          </Text>
                        )}
                      </Tag>
                    </WrapItem>
                  );
                })}
              </Wrap>
            </Stack>
          )}

          <Flex
            direction={{ base: "column", md: "row" }}
            justify="space-between"
            align={{ base: "flex-start", md: "center" }}
            gap={4}
            wrap="wrap"
          >
            <Stack spacing={2} flex={1} minW={0}>
              <Flex gap={4} flexWrap="wrap" fontSize="sm" color="text.subtle">
                <Text>📁 {release.files.length} files</Text>
                {video.length > 0 && <Text>🎬 {video.length} video</Text>}
                {subtitle.length > 0 && (
                  <Text>📝 {subtitle.length} subtitle</Text>
                )}
                {other.length > 0 && <Text>📄 {other.length} other</Text>}
              </Flex>

              <Flex gap={4} flexWrap="wrap" fontSize="sm" color="text.muted">
                <Text>Added: {formatDate(release.added_date)}</Text>
                {release.completed_date && (
                  <Text>Completed: {formatDate(release.completed_date)}</Text>
                )}
              </Flex>
            </Stack>

            {showActions && (
              <Flex
                justify={{ base: "flex-start", md: "flex-end" }}
                align="center"
                gap={2}
                wrap="wrap"
              >
                <Button
                  onClick={() => onViewFiles?.(release)}
                  size="sm"
                  colorScheme="blue"
                  variant="solid"
                  isDisabled={isLoading}
                >
                  Files
                </Button>

                {isActive && onPause && (
                  <Button
                    onClick={() => handleAction(() => onPause(release.id))}
                    size="sm"
                    colorScheme="orange"
                    variant="solid"
                    isDisabled={isLoading}
                  >
                    Pause
                  </Button>
                )}

                {release.status === "pending" && onResume && (
                  <Button
                    onClick={() => handleAction(() => onResume(release.id))}
                    size="sm"
                    colorScheme="green"
                    variant="solid"
                    isDisabled={isLoading}
                  >
                    Resume
                  </Button>
                )}

                {onDelete && (
                  <IconButton
                    aria-label="Delete release"
                    icon={<DeleteIcon />}
                    variant="ghost"
                    size="sm"
                    colorScheme="red"
                    onClick={() => setDeleteDialogOpen(true)}
                    isDisabled={isLoading}
                  />
                )}
              </Flex>
            )}
          </Flex>
        </Stack>
      </Card>
      {deleteDialog}
    </>
  );
};

export default ReleaseCard;
