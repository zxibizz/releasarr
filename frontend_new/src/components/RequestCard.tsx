import {
  Badge,
  Card,
  Flex,
  Heading,
  HStack,
  LinkBox,
  LinkOverlay,
  Stack,
  Tag,
  Text,
} from "@chakra-ui/react";
import React from "react";
import { Link as RouterLink } from "react-router-dom";
import { MediaRequest } from "../types";
import { formatDate, formatRuntime, getStatusIcon } from "../utils/formatters";

interface RequestCardProps {
  request: MediaRequest;
}

const statusColorScheme: Record<MediaRequest["status"], string> = {
  pending: "yellow",
  searching: "purple",
  downloading: "blue",
  completed: "green",
  failed: "red",
};

export const RequestCard: React.FC<RequestCardProps> = ({ request }) => {
  const isMovie = request.type === "movie";
  const statusIcon = getStatusIcon(request.status);

  return (
    <Card
      as={LinkBox}
      role="group"
      cursor="pointer"
      transition="all 0.2s ease"
      _hover={{ shadow: "lg", transform: "translateY(-2px)" }}
      p={{ base: 5, md: 6 }}
    >
      <Stack spacing={4} height="100%">
        <Flex
          align={{ base: "flex-start", md: "center" }}
          justify="space-between"
          gap={4}
          flexWrap="wrap"
        >
          <Stack spacing={1} minW={0} flex={1}>
            <Heading size="md" noOfLines={2}>
              <LinkOverlay
                as={RouterLink}
                to={`/request/${request.id}`}
                _hover={{ textDecoration: "none" }}
              >
                {request.title}
              </LinkOverlay>
            </Heading>
            <Text fontSize="sm" color="text.subtle">
              {request.year}
              {!isMovie && ` • Season ${request.season_number}`}
              {isMovie && ` • ${formatRuntime(request.runtime)}`}
            </Text>
          </Stack>

          <Badge
            colorScheme={statusColorScheme[request.status]}
            variant="subtle"
            display="inline-flex"
            alignItems="center"
            gap={1}
            fontSize="xs"
            px={3}
            py={1}
            borderRadius="md"
            textTransform="capitalize"
          >
            <Text as="span" fontSize="md" lineHeight={1}>
              {statusIcon}
            </Text>
            {request.status}
          </Badge>
        </Flex>

        <HStack spacing={2} flexWrap="wrap">
          <Tag
            colorScheme={isMovie ? "red" : "blue"}
            variant="subtle"
            borderRadius="full"
            px={3}
            py={1}
            fontSize="xs"
            fontWeight="600"
            textTransform="uppercase"
            letterSpacing="0.08em"
          >
            <Text as="span" mr={1}>
              {isMovie ? "🎬" : "📺"}
            </Text>
            {request.type}
          </Tag>

          {request.genres.slice(0, 2).map((genre) => (
            <Tag
              key={genre}
              variant="subtle"
              colorScheme="gray"
              borderRadius="md"
              px={2}
              py={1}
              fontSize="xs"
            >
              {genre}
            </Tag>
          ))}

          {request.genres.length > 2 && (
            <Tag
              variant="subtle"
              colorScheme="gray"
              borderRadius="md"
              px={2}
              py={1}
              fontSize="xs"
            >
              +{request.genres.length - 2}
            </Tag>
          )}
        </HStack>

        <Text fontSize="sm" color="slate.200" noOfLines={3}>
          {request.overview}
        </Text>

        {!isMovie && (
          <Text fontSize="xs" color="text.muted">
            <Text as="span">{request.total_episodes} episodes</Text>
            <Text as="span" mx={2}>
              •
            </Text>
            <Text as="span">
              {request.series_title} ({request.series_year})
            </Text>
          </Text>
        )}

        <Flex
          mt="auto"
          justify="space-between"
          align="center"
          fontSize="xs"
          color="text.muted"
        >
          <Text>Created {formatDate(request.created_at)}</Text>
          <Text textTransform="capitalize">{request.type}</Text>
        </Flex>
      </Stack>
    </Card>
  );
};
