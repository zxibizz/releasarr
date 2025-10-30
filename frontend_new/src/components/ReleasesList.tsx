import {
  Alert,
  AlertDescription,
  AlertIcon,
  AlertTitle,
  Box,
  Button,
  Card,
  Center,
  Flex,
  Heading,
  Select,
  SimpleGrid,
  Spinner,
  Stack,
  Text,
  VStack,
} from "@chakra-ui/react";
import React, { useMemo, useState } from "react";
import { useReleasesByRequest } from "../hooks/useReleases";
import { Release } from "../types";
import {
  filterReleasesByStatus,
  formatSpeed,
  getActiveDownloads,
  getCompletedReleases,
  getTotalDownloadSpeed,
  getTotalUploadSpeed,
  sortReleasesByDate,
  sortReleasesBySize,
  sortReleasesByStatus,
} from "../utils/releaseHelpers";
import ReleaseCard from "./ReleaseCard";

interface ReleasesListProps {
  requestId: string;
  onPauseRelease?: (id: string) => void;
  onResumeRelease?: (id: string) => void;
  onDeleteRelease?: (id: string) => void;
  onViewFiles?: (release: Release) => void;
  onEditMapping?: (release: Release) => void;
  compact?: boolean;
  showStats?: boolean;
}

type SortOption = "status" | "date" | "size";
type FilterOption =
  | "all"
  | "downloading"
  | "pending"
  | "seeding"
  | "completed"
  | "failed";

const sortLabels: Record<SortOption, string> = {
  status: "Status",
  date: "Date",
  size: "Size",
};

const filterOptions: { key: FilterOption; label: string }[] = [
  { key: "all", label: "All" },
  { key: "downloading", label: "Downloading" },
  { key: "pending", label: "Pending" },
  { key: "seeding", label: "Seeding" },
  { key: "completed", label: "Completed" },
  { key: "failed", label: "Failed" },
];

const ReleasesList: React.FC<ReleasesListProps> = ({
  requestId,
  onPauseRelease,
  onResumeRelease,
  onDeleteRelease,
  onViewFiles,
  onEditMapping,
  compact = false,
  showStats = true,
}) => {
  const { releases, loading, error, refetch } = useReleasesByRequest(requestId);
  const [sortBy, setSortBy] = useState<SortOption>("status");
  const [filterBy, setFilterBy] = useState<FilterOption>("all");
  const [sortAscending, setSortAscending] = useState(false);

  const filteredAndSortedReleases = useMemo(() => {
    let filtered = releases;

    if (filterBy !== "all") {
      filtered = filterReleasesByStatus(
        releases,
        filterBy as Release["status"]
      );
    }

    switch (sortBy) {
      case "status":
        return sortReleasesByStatus(filtered);
      case "date":
        return sortReleasesByDate(filtered, sortAscending);
      case "size":
        return sortReleasesBySize(filtered, sortAscending);
      default:
        return filtered;
    }
  }, [releases, sortBy, filterBy, sortAscending]);

  const stats = useMemo(() => {
    const activeDownloads = getActiveDownloads(releases);
    const completedReleases = getCompletedReleases(releases);
    const totalDownloadSpeed = getTotalDownloadSpeed(releases);
    const totalUploadSpeed = getTotalUploadSpeed(releases);

    return {
      total: releases.length,
      active: activeDownloads.length,
      completed: completedReleases.length,
      downloadSpeed: totalDownloadSpeed,
      uploadSpeed: totalUploadSpeed,
    };
  }, [releases]);

  const handleSortChange = (newSort: SortOption) => {
    if (sortBy === newSort) {
      setSortAscending(!sortAscending);
    } else {
      setSortBy(newSort);
      setSortAscending(false);
    }
  };

  if (loading) {
    return (
      <Center py={10} flexDirection="column" gap={4} color="text.subtle">
        <Spinner size="lg" color="brand.400" />
        <Text>Loading releases...</Text>
      </Center>
    );
  }

  if (error) {
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
          <AlertDescription>{error}</AlertDescription>
        </Box>
        <Button
          variant="outline"
          colorScheme="blue"
          size="sm"
          onClick={refetch}
        >
          Try Again
        </Button>
      </Alert>
    );
  }

  if (releases.length === 0) {
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
          No torrent releases have been added for this request yet.
        </Text>
      </VStack>
    );
  }

  return (
    <Stack spacing={6}>
      {showStats && (
        <Card
          p={6}
          bg="bg.subtle"
          borderWidth="1px"
          borderColor="border.muted"
          borderRadius="lg"
        >
          <SimpleGrid columns={{ base: 1, sm: 2, md: 5 }} spacing={4}>
            <StatItem label="Total" value={stats.total} colorScheme="purple" />
            <StatItem
              label="Active"
              value={stats.active}
              colorScheme="orange"
            />
            <StatItem
              label="Completed"
              value={stats.completed}
              colorScheme="green"
            />
            <StatItem
              label="Download"
              value={formatSpeed(stats.downloadSpeed)}
              colorScheme="blue"
            />
            <StatItem
              label="Upload"
              value={formatSpeed(stats.uploadSpeed)}
              colorScheme="teal"
            />
          </SimpleGrid>
        </Card>
      )}

      <Card
        p={6}
        bg="bg.subtle"
        borderWidth="1px"
        borderColor="border.muted"
        borderRadius="lg"
      >
        <Stack spacing={4}>
          <Flex
            direction={{ base: "column", lg: "row" }}
            gap={4}
            justify="space-between"
            align={{ base: "flex-start", lg: "center" }}
          >
            <Flex align="center" gap={3} wrap="wrap">
              <Text fontWeight="600">Filter:</Text>
              <Select
                value={filterBy}
                onChange={(e) => setFilterBy(e.target.value as FilterOption)}
                maxW="220px"
                size="sm"
                variant="filled"
              >
                {filterOptions.map((option) => (
                  <option key={option.key} value={option.key}>
                    {option.label} (
                    {option.key === "all"
                      ? releases.length
                      : filterReleasesByStatus(
                          releases,
                          option.key as Release["status"]
                        ).length}
                    )
                  </option>
                ))}
              </Select>
            </Flex>

            <Flex align="center" gap={2} wrap="wrap">
              <Text fontWeight="600">Sort by:</Text>
              {(["status", "date", "size"] as SortOption[]).map((option) => {
                const isActive = sortBy === option;
                return (
                  <Button
                    key={option}
                    size="sm"
                    colorScheme="blue"
                    variant={isActive ? "solid" : "outline"}
                    onClick={() => handleSortChange(option)}
                  >
                    {sortLabels[option]}{" "}
                    {isActive && (sortAscending ? "↑" : "↓")}
                  </Button>
                );
              })}
            </Flex>

            <Button
              size="sm"
              variant="outline"
              colorScheme="blue"
              onClick={refetch}
            >
              🔄 Refresh
            </Button>
          </Flex>

          {filterBy !== "all" && (
            <Text fontSize="sm" color="text.subtle">
              Showing {filteredAndSortedReleases.length} of {releases.length}{" "}
              releases
            </Text>
          )}
        </Stack>
      </Card>

      <Stack spacing={compact ? 3 : 4}>
        {filteredAndSortedReleases.length === 0 ? (
          <Card p={6} textAlign="center">
            <Stack spacing={3} align="center">
              <Text fontSize="3xl">🔍</Text>
              <Heading size="sm">No releases match your filter</Heading>
              <Text color="text.subtle" fontSize="sm">
                Try adjusting your filter criteria to see more results.
              </Text>
              <Button
                size="sm"
                colorScheme="blue"
                onClick={() => setFilterBy("all")}
              >
                Show All Releases
              </Button>
            </Stack>
          </Card>
        ) : (
          filteredAndSortedReleases.map((release) => (
            <ReleaseCard
              key={release.id}
              release={release}
              onPause={onPauseRelease}
              onResume={onResumeRelease}
              onDelete={onDeleteRelease}
              onViewFiles={onViewFiles}
              onEditMapping={onEditMapping}
              compact={compact}
            />
          ))
        )}
      </Stack>
    </Stack>
  );
};

interface StatItemProps {
  label: string;
  value: number | string;
  colorScheme: keyof typeof STAT_COLOR_MAP;
}

const STAT_COLOR_MAP = {
  blue: {
    bg: "rgba(59, 130, 246, 0.2)",
    border: "rgba(59, 130, 246, 0.35)",
    text: "blue.200",
  },
  teal: {
    bg: "rgba(45, 212, 191, 0.18)",
    border: "rgba(45, 212, 191, 0.35)",
    text: "teal.200",
  },
  green: {
    bg: "rgba(34, 197, 94, 0.18)",
    border: "rgba(34, 197, 94, 0.32)",
    text: "green.200",
  },
  orange: {
    bg: "rgba(251, 146, 60, 0.22)",
    border: "rgba(251, 146, 60, 0.35)",
    text: "orange.200",
  },
  purple: {
    bg: "rgba(139, 92, 246, 0.2)",
    border: "rgba(139, 92, 246, 0.38)",
    text: "purple.200",
  },
} as const;

const StatItem: React.FC<StatItemProps> = ({ label, value, colorScheme }) => {
  const colors = STAT_COLOR_MAP[colorScheme] ?? STAT_COLOR_MAP.blue;

  return (
    <Box
      bg={colors.bg}
      borderWidth="1px"
      borderColor={colors.border}
      borderRadius="lg"
      p={4}
      textAlign="left"
    >
      <Text fontSize="2xl" fontWeight="700" color={colors.text}>
        {value}
      </Text>
      <Text fontSize="sm" color="text.subtle">
        {label}
      </Text>
    </Box>
  );
};

export default ReleasesList;
