import {
  Alert,
  AlertDescription,
  AlertIcon,
  Box,
  Button,
  Card,
  Center,
  Flex,
  Heading,
  Input,
  Spinner,
  Stack,
  Tag,
  Text,
  useToast,
} from "@chakra-ui/react";
import React, { useEffect, useRef, useState } from "react";
import { useReleaseSearch } from "../hooks/useReleaseSearch";
import { ReleaseSearchResult } from "../types";

interface ReleaseSearchProps {
  requestId: string;
  requestTitle: string;
  onDownloadQueued?: () => void;
  prefillQuery?: string | null;
  focusTrigger?: number;
}

const qualityColorScheme: Record<string, string> = {
  "2160p": "purple",
  "1080p": "blue",
  "720p": "green",
};

export const ReleaseSearch: React.FC<ReleaseSearchProps> = ({
  requestId,
  requestTitle,
  onDownloadQueued,
  prefillQuery,
  focusTrigger,
}) => {
  const { searchState, search, clearSearch, selectReleaseCandidate } =
    useReleaseSearch();
  const [query, setQuery] = useState("");
  const [downloadingCandidateId, setDownloadingCandidateId] = useState<
    string | null
  >(null);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const toast = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      try {
        await search(query.trim(), requestId);
      } catch (error) {
        const message =
          error instanceof Error ? error.message : "Search failed";
        toast({
          title: "Search failed",
          description: message,
          status: "error",
          duration: 4000,
          isClosable: true,
        });
      }
    }
  };

  const handleClear = () => {
    setQuery("");
    clearSearch();
    setDownloadingCandidateId(null);
  };

  const handleCandidateSelect = async (candidate: ReleaseSearchResult) => {
    setDownloadingCandidateId(candidate.release_id);
    try {
      const response = await selectReleaseCandidate(candidate, requestId);
      toast({
        title: "Download queued",
        description:
          response?.message ?? `${candidate.release_name} queued for download`,
        status: "success",
        duration: 4000,
        isClosable: true,
      });
      onDownloadQueued?.();
      handleClear();
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to queue download";
      toast({
        title: "Download failed",
        description: message,
        status: "error",
        duration: 4000,
        isClosable: true,
      });
    } finally {
      setDownloadingCandidateId(null);
    }
  };

  useEffect(() => {
    if (prefillQuery === undefined || prefillQuery === null) {
      return;
    }

    setQuery(prefillQuery.trim());
    requestAnimationFrame(() => {
      inputRef.current?.focus({ preventScroll: true });
      inputRef.current?.select();
    });
  }, [prefillQuery]);

  useEffect(() => {
    if (!focusTrigger || focusTrigger <= 0) {
      return;
    }

    requestAnimationFrame(() => {
      inputRef.current?.focus({ preventScroll: true });
      inputRef.current?.select();
    });
  }, [focusTrigger]);

  return (
    <Card p={{ base: 5, md: 6 }}>
      <Stack spacing={6}>
        <Heading size="md">🔍 Search Release Sources</Heading>

        <Box as="form" onSubmit={handleSubmit}>
          <Flex direction={{ base: "column", md: "row" }} gap={3}>
            <Input
              ref={inputRef}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={`Search release sources for "${requestTitle}"...`}
              size="md"
            />
            <Flex gap={2}>
              <Button
                type="submit"
                isDisabled={!query.trim() || searchState.loading}
              >
                {searchState.loading ? "Searching..." : "Search"}
              </Button>
              {(query || searchState.results.length > 0) && (
                <Button
                  type="button"
                  variant="outline"
                  colorScheme="gray"
                  onClick={handleClear}
                >
                  Clear
                </Button>
              )}
            </Flex>
          </Flex>
        </Box>

        {searchState.loading && (
          <Center py={10} flexDirection="column" gap={4} color="text.subtle">
            <Spinner size="lg" color="brand.400" />
            <Text>Searching release sources...</Text>
          </Center>
        )}

        {searchState.error && (
          <Alert
            status="error"
            variant="left-accent"
            borderRadius="lg"
            alignItems="flex-start"
          >
            <AlertIcon />
            <AlertDescription>{searchState.error}</AlertDescription>
          </Alert>
        )}

        {searchState.results.length > 0 && !searchState.loading && (
          <Stack spacing={4}>
            <Flex
              justify="space-between"
              align={{ base: "flex-start", md: "center" }}
              direction={{ base: "column", md: "row" }}
              gap={2}
            >
              <Heading size="sm">Search Results</Heading>
              <Text color="text.subtle" fontSize="sm">
                {searchState.results.length} results for "{searchState.query}"
              </Text>
            </Flex>

            <Stack spacing={3}>
              {searchState.results.map((candidate) => {
                const qualityLabel = candidate.quality ?? "Unknown";
                const qualityColor = qualityColorScheme[qualityLabel] || "gray";
                const seedersLabel = candidate.seeders ?? 0;
                const leechersLabel = candidate.leechers ?? 0;
                return (
                  <Flex
                    key={candidate.release_id}
                    direction={{ base: "column", md: "row" }}
                    justify="space-between"
                    align={{ base: "flex-start", md: "center" }}
                    gap={4}
                    p={4}
                    borderWidth="1px"
                    borderColor="border.muted"
                    borderRadius="lg"
                    bg="bg.subtle"
                  >
                    <Stack spacing={2} flex={1} minW={0}>
                      <Text
                        fontWeight="600"
                        fontSize="sm"
                        color="slate.100"
                        noOfLines={2}
                      >
                        {candidate.release_name}
                      </Text>
                      <Flex
                        gap={3}
                        wrap="wrap"
                        fontSize="xs"
                        color="text.subtle"
                      >
                        <Tag
                          colorScheme={qualityColor}
                          variant="subtle"
                          borderRadius="full"
                          px={3}
                          py={1}
                        >
                          {qualityLabel}
                        </Tag>
                        <Text>📦 {candidate.size}</Text>
                        <Text color="green.300">⬆️ {seedersLabel}</Text>
                        <Text color="red.300">⬇️ {leechersLabel}</Text>
                        {candidate.source && <Text>🏷️ {candidate.source}</Text>}
                        {candidate.magnet_link && (
                          <Button
                            as="a"
                            href={candidate.magnet_link}
                            target="_self"
                            rel="noopener noreferrer"
                            size="xs"
                            variant="link"
                            colorScheme="orange"
                            px={0}
                          >
                            Magnet link ↗
                          </Button>
                        )}
                        {candidate.info_url && (
                          <Button
                            as="a"
                            href={candidate.info_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            size="xs"
                            variant="link"
                            colorScheme="blue"
                            px={0}
                          >
                            View info ↗
                          </Button>
                        )}
                        {candidate.torrent_file_url && (
                          <Button
                            as="a"
                            href={candidate.torrent_file_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            size="xs"
                            variant="link"
                            colorScheme="green"
                            px={0}
                          >
                            Torrent file ↗
                          </Button>
                        )}
                      </Flex>
                    </Stack>

                    <Button
                      onClick={() => handleCandidateSelect(candidate)}
                      size="sm"
                      isLoading={
                        downloadingCandidateId === candidate.release_id
                      }
                      loadingText="Queuing..."
                      isDisabled={
                        !!downloadingCandidateId &&
                        downloadingCandidateId !== candidate.release_id
                      }
                    >
                      Download
                    </Button>
                  </Flex>
                );
              })}
            </Stack>
          </Stack>
        )}

        {searchState.query &&
          searchState.results.length === 0 &&
          !searchState.loading &&
          !searchState.error && (
            <Stack
              spacing={3}
              py={10}
              align="center"
              borderWidth="1px"
              borderColor="border.muted"
              borderRadius="xl"
              bg="bg.subtle"
            >
              <Text fontSize="4xl">🔍</Text>
              <Heading size="sm">No release sources found</Heading>
              <Text color="text.subtle" fontSize="sm" textAlign="center" px={6}>
                Try adjusting your search terms or check back later.
              </Text>
            </Stack>
          )}
      </Stack>
    </Card>
  );
};
