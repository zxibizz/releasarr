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
      filtered = filterReleasesByStatus(releases, filterBy as Release["status"]);
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
        <Button variant="outline" colorScheme="blue" size="sm" onClick={refetch}>
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
        <Card p={6}>
          <SimpleGrid columns={{ base: 2, md: 5 }} spacing={4} textAlign="center">
            <StatItem label="Total" value={stats.total} accent="brand.400" />
            <StatItem label="Active" value={stats.active} accent="orange.300" />
            <StatItem label="Completed" value={stats.completed} accent="green.300" />
            <StatItem label="Download" value={formatSpeed(stats.downloadSpeed)} accent="brand.300" />
            <StatItem label="Upload" value={formatSpeed(stats.uploadSpeed)} accent="green.300" />
          </SimpleGrid>
        </Card>
      )}

      <Card p={6}>
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
                    {option.label} ({
                      option.key === "all"
                        ? releases.length
                        : filterReleasesByStatus(releases, option.key as Release["status"]).length
                    })
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
                    {sortLabels[option]} {isActive && (sortAscending ? "↑" : "↓")}
                  </Button>
                );
              })}
            </Flex>

            <Button size="sm" variant="outline" colorScheme="blue" onClick={refetch}>
              🔄 Refresh
            </Button>
          </Flex>

          {filterBy !== "all" && (
            <Text fontSize="sm" color="text.subtle">
              Showing {filteredAndSortedReleases.length} of {releases.length} releases
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
              <Button size="sm" colorScheme="blue" onClick={() => setFilterBy("all")}>
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
  accent: string;
}

const StatItem: React.FC<StatItemProps> = ({ label, value, accent }) => (
  <Box>
    <Text fontSize="2xl" fontWeight="700" color={accent}>
      {value}
    </Text>
    <Text fontSize="sm" color="text.subtle">
      {label}
    </Text>
  </Box>
);

export default ReleasesList;
