import {
  Badge,
  Box,
  Card,
  Flex,
  Heading,
  Link,
  SimpleGrid,
  Stack,
  Tag,
  Text,
  Wrap,
  WrapItem,
} from "@chakra-ui/react";
import React from "react";
import { MediaRequest } from "../types";
import { formatDate, formatRuntime, getStatusIcon } from "../utils/formatters";

interface MediaInfoProps {
  request: MediaRequest;
}

const statusColorScheme: Record<MediaRequest["status"], string> = {
  pending: "yellow",
  searching: "purple",
  downloading: "blue",
  completed: "green",
  failed: "red",
};

export const MediaInfo: React.FC<MediaInfoProps> = ({ request }) => {
  const isMovie = request.type === "movie";
  const statusIcon = getStatusIcon(request.status);

  return (
    <Card p={{ base: 5, md: 6 }}>
      <Stack spacing={6}>
        <Flex
          direction={{ base: "column", md: "row" }}
          justify="space-between"
          align={{ base: "flex-start", md: "center" }}
          gap={4}
        >
          <Box>
            <Heading size="lg" mb={2}>
              {request.title}
            </Heading>
            <Flex align="center" gap={2} wrap="wrap" color="text.subtle">
              <Text fontSize="lg" fontWeight="600">
                {request.year}
              </Text>
              <Text>•</Text>
              {isMovie ? (
                <Text fontSize="lg">{formatRuntime(request.runtime)}</Text>
              ) : (
                <Text fontSize="lg">Season {request.season_number}</Text>
              )}
            </Flex>
          </Box>

          <Badge
            colorScheme={statusColorScheme[request.status]}
            variant="subtle"
            display="inline-flex"
            alignItems="center"
            gap={1}
            fontSize="sm"
            px={3}
            py={1.5}
            borderRadius="md"
            textTransform="capitalize"
          >
            <Text as="span" fontSize="lg" lineHeight={1}>
              {statusIcon}
            </Text>
            {request.status}
          </Badge>
        </Flex>

        <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4}>
          <InfoItem label="Type">
            {isMovie ? "🎬 Movie" : "📺 TV Series"}
          </InfoItem>
          <InfoItem label="Created">{formatDate(request.created_at)}</InfoItem>
          <InfoItem label="Updated">{formatDate(request.updated_at)}</InfoItem>
          <InfoItem label="IMDb">
            <Link
              href={`https://www.imdb.com/title/${request.imdb_id}`}
              isExternal
              color="brand.400"
              fontWeight="600"
            >
              {request.imdb_id}
            </Link>
          </InfoItem>
          {!isMovie && (
            <InfoItem label="Series">
              {request.series_title} ({request.series_year})
            </InfoItem>
          )}
          {!isMovie && (
            <InfoItem label="Episodes">{request.total_episodes}</InfoItem>
          )}
        </SimpleGrid>

        <Box>
          <Heading size="sm" mb={3}>
            Genres
          </Heading>
          <Wrap spacing={2}>
            {request.genres.map((genre) => (
              <WrapItem key={genre}>
                <Tag variant="subtle" colorScheme="gray" borderRadius="full" px={3} py={1}>
                  {genre}
                </Tag>
              </WrapItem>
            ))}
          </Wrap>
        </Box>

        <Box>
          <Heading size="sm" mb={3}>
            Overview
          </Heading>
          <Text fontSize="sm" color="slate.200" lineHeight="tall">
            {request.overview}
          </Text>
        </Box>
      </Stack>
    </Card>
  );
};

interface InfoItemProps {
  label: string;
  children: React.ReactNode;
}

const InfoItem: React.FC<InfoItemProps> = ({ label, children }) => (
  <Box
    bg="bg.subtle"
    borderWidth="1px"
    borderColor="border.muted"
    borderRadius="lg"
    p={4}
  >
    <Text fontSize="xs" textTransform="uppercase" color="text.subtle" letterSpacing="0.08em">
      {label}
    </Text>
    <Text fontSize="sm" fontWeight="600" mt={2} color="slate.100">
      {children}
    </Text>
  </Box>
);
