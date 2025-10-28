import {
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
import { ChevronDownIcon, ChevronUpIcon } from "@chakra-ui/icons";
import React, { useState } from "react";
import { Release } from "../types";
import {
  calculateReleaseProgress,
  formatFileSize,
  formatProgress,
  formatRatio,
  formatSpeed,
  getReleaseHealthScore,
  getStatusIcon,
  groupFilesByType,
  isReleaseActive,
} from "../utils/releaseHelpers";

interface ReleaseCardProps {
  release: Release;
  onPause?: (id: string) => void;
  onResume?: (id: string) => void;
  onDelete?: (id: string) => void;
  onViewFiles?: (release: Release) => void;
  onEditMapping?: (release: Release) => void;
  showActions?: boolean;
  compact?: boolean;
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

const ReleaseCard: React.FC<ReleaseCardProps> = ({
  release,
  onPause,
  onResume,
  onDelete,
  onViewFiles,
  onEditMapping,
  showActions = true,
  compact = false,
}) => {
  const [showDetails, setShowDetails] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const progress = calculateReleaseProgress(release);
  const isActive = isReleaseActive(release);
  const healthScore = getReleaseHealthScore(release);
  const { video, subtitle, other } = groupFilesByType(release.files);

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

  if (compact) {
    return (
      <Card p={4}>
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
                    Health: {" "}
                    <Text as="span" fontWeight="600" color={getHealthColor(healthScore)}>
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
    );
  }

  return (
    <Card p={{ base: 5, md: 6 }}>
      <Stack spacing={6}>
        <Flex
          direction={{ base: "column", md: "row" }}
          align={{ base: "flex-start", md: "flex-start" }}
          justify="space-between"
          gap={6}
        >
          <Stack spacing={3} flex={1} minW={0}>
            <Flex align="center" gap={3} wrap="wrap">
              <Text fontSize="2xl">{getStatusIcon(release.status)}</Text>
              <Text fontWeight="700" fontSize="lg" color="slate.100" noOfLines={2}>
                {release.name}
              </Text>
            </Flex>
            <Flex gap={3} wrap="wrap" align="center" fontSize="sm" color="text.subtle">
              <Badge
                colorScheme={statusColorScheme[release.status]}
                variant="subtle"
                textTransform="capitalize"
                px={3}
                py={1}
              >
                {release.status}
              </Badge>
              <Text>{formatFileSize(release.size)}</Text>
              {release.quality && (
                <Tag colorScheme="blue" borderRadius="full" px={3} py={1}>
                  {release.quality}
                </Tag>
              )}
            </Flex>
          </Stack>

          {showActions && (
            <Stack spacing={2} minW={{ base: "100%", md: "160px" }}>
              <Button
                onClick={() => onViewFiles?.(release)}
                variant="outline"
                colorScheme="gray"
                size="sm"
                isDisabled={isLoading}
              >
                View Files
              </Button>

              {release.files.some((f) => !f.episode_mapping && !f.request_mapping) ? (
                <Button
                  onClick={() => onEditMapping?.(release)}
                  size="sm"
                  colorScheme="yellow"
                  variant="solid"
                  isDisabled={isLoading}
                >
                  Map Files
                </Button>
              ) : (
                <Button
                  onClick={() => onViewFiles?.(release)}
                  size="sm"
                  colorScheme="blue"
                  variant="solid"
                  isDisabled={isLoading}
                >
                  View Mapping
                </Button>
              )}

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
                <Button
                  onClick={() => handleAction(() => onDelete(release.id))}
                  size="sm"
                  colorScheme="red"
                  variant="solid"
                  isDisabled={isLoading}
                >
                  Delete
                </Button>
              )}
            </Stack>
          )}
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

        <Grid templateColumns={{ base: "repeat(2, minmax(0, 1fr))", md: "repeat(4, minmax(0, 1fr))" }} gap={4}>
          <GridItem textAlign="center">
            <Text fontSize="xs" color="text.subtle">
              Seeders
            </Text>
            <Text fontSize="lg" fontWeight="600" color="green.300">
              {release.seeders}
            </Text>
          </GridItem>
          <GridItem textAlign="center">
            <Text fontSize="xs" color="text.subtle">
              Leechers
            </Text>
            <Text fontSize="lg" fontWeight="600" color="blue.300">
              {release.leechers}
            </Text>
          </GridItem>
          <GridItem textAlign="center">
            <Text fontSize="xs" color="text.subtle">
              Ratio
            </Text>
            <Text fontSize="lg" fontWeight="600" color="purple.300">
              {formatRatio(release.ratio)}
            </Text>
          </GridItem>
          <GridItem textAlign="center">
            <Text fontSize="xs" color="text.subtle">
              Health
            </Text>
            <Text fontSize="lg" fontWeight="600" color={getHealthColor(healthScore)}>
              {healthScore}%
            </Text>
          </GridItem>
        </Grid>

        {(release.download_speed > 0 || release.upload_speed > 0) && (
          <Flex gap={6} flexWrap="wrap" fontSize="sm" color="slate.100">
            {release.download_speed > 0 && (
              <Flex align="center" gap={2}>
                <Text color="blue.300">↓</Text>
                <Text fontWeight="600">{formatSpeed(release.download_speed)}</Text>
              </Flex>
            )}
            {release.upload_speed > 0 && (
              <Flex align="center" gap={2}>
                <Text color="green.300">↑</Text>
                <Text fontWeight="600">{formatSpeed(release.upload_speed)}</Text>
              </Flex>
            )}
          </Flex>
        )}

        <Flex gap={4} flexWrap="wrap" fontSize="sm" color="text.subtle">
          <Text>📁 {release.files.length} files</Text>
          {video.length > 0 && <Text>🎬 {video.length} video</Text>}
          {subtitle.length > 0 && <Text>📝 {subtitle.length} subtitle</Text>}
          {other.length > 0 && <Text>📄 {other.length} other</Text>}
        </Flex>

        <Flex gap={4} flexWrap="wrap" fontSize="sm" color="text.muted">
          <Text>Added: {formatDate(release.added_date)}</Text>
          {release.completed_date && <Text>Completed: {formatDate(release.completed_date)}</Text>}
        </Flex>

        {release.request_ids.length > 0 && (
          <Stack spacing={2}>
            <Text fontWeight="600" color="text.subtle">
              Related Requests
            </Text>
            <Wrap spacing={2}>
              {release.request_ids.map((requestId) => (
                <WrapItem key={requestId}>
                  <Tag colorScheme="blue" variant="subtle" borderRadius="full" px={3} py={1} fontSize="xs">
                    {requestId}
                  </Tag>
                </WrapItem>
              ))}
            </Wrap>
          </Stack>
        )}
      </Stack>
    </Card>
  );
};

export default ReleaseCard;
