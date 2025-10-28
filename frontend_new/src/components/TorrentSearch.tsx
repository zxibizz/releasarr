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
} from "@chakra-ui/react";
import React, { useState } from "react";
import { useTorrentSearch } from "../hooks/useTorrentSearch";
import { TorrentResult } from "../types";

interface TorrentSearchProps {
  requestId: string;
  requestTitle: string;
}

const qualityColorScheme: Record<string, string> = {
  "2160p": "purple",
  "1080p": "blue",
  "720p": "green",
};

export const TorrentSearch: React.FC<TorrentSearchProps> = ({
  requestId,
  requestTitle,
}) => {
  const { searchState, search, clearSearch, selectTorrent } =
    useTorrentSearch();
  const [query, setQuery] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      search(query.trim());
    }
  };

  const handleClear = () => {
    setQuery("");
    clearSearch();
  };

  const handleTorrentSelect = (torrent: TorrentResult) => {
    selectTorrent(torrent);
    alert(`Selected torrent: ${torrent.name}`);
  };

  return (
    <Card p={{ base: 5, md: 6 }}>
      <Stack spacing={6}>
        <Heading size="md">🔍 Search Torrents</Heading>

        <Box as="form" onSubmit={handleSubmit}>
          <Flex direction={{ base: "column", md: "row" }} gap={3}>
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={`Search torrents for "${requestTitle}"...`}
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
                <Button type="button" variant="outline" colorScheme="gray" onClick={handleClear}>
                  Clear
                </Button>
              )}
            </Flex>
          </Flex>
        </Box>

        {searchState.loading && (
          <Center py={10} flexDirection="column" gap={4} color="text.subtle">
            <Spinner size="lg" color="brand.400" />
            <Text>Searching torrents...</Text>
          </Center>
        )}

        {searchState.error && (
          <Alert status="error" variant="left-accent" borderRadius="lg" alignItems="flex-start">
            <AlertIcon />
            <AlertDescription>{searchState.error}</AlertDescription>
          </Alert>
        )}

        {searchState.results.length > 0 && !searchState.loading && (
          <Stack spacing={4}>
            <Flex justify="space-between" align={{ base: "flex-start", md: "center" }} direction={{ base: "column", md: "row" }} gap={2}>
              <Heading size="sm">Search Results</Heading>
              <Text color="text.subtle" fontSize="sm">
                {searchState.results.length} results for "{searchState.query}"
              </Text>
            </Flex>

            <Stack spacing={3}>
              {searchState.results.map((torrent) => (
                <Flex
                  key={torrent.id}
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
                    <Text fontWeight="600" fontSize="sm" color="slate.100" noOfLines={2}>
                      {torrent.name}
                    </Text>
                    <Flex gap={3} wrap="wrap" fontSize="xs" color="text.subtle">
                      <Tag
                        colorScheme={qualityColorScheme[torrent.quality] || "gray"}
                        variant="subtle"
                        borderRadius="full"
                        px={3}
                        py={1}
                      >
                        {torrent.quality}
                      </Tag>
                      <Text>📦 {torrent.size}</Text>
                      <Text color="green.300">⬆️ {torrent.seeders}</Text>
                      <Text color="red.300">⬇️ {torrent.leechers}</Text>
                      <Text>🏷️ {torrent.source}</Text>
                    </Flex>
                  </Stack>

                  <Button onClick={() => handleTorrentSelect(torrent)} size="sm">
                    Select
                  </Button>
                </Flex>
              ))}
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
              <Heading size="sm">No torrents found</Heading>
              <Text color="text.subtle" fontSize="sm" textAlign="center" px={6}>
                Try adjusting your search terms or check back later.
              </Text>
            </Stack>
          )}
      </Stack>
    </Card>
  );
};
