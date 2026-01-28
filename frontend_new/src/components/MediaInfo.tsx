import {
  AspectRatio,
  Badge,
  Box,
  Card,
  Flex,
  Heading,
  Image,
  SimpleGrid,
  Stack,
  Tag,
  Text,
  Wrap,
  WrapItem,
} from '@chakra-ui/react';
import React from 'react';

import { requestStatusStyles } from '@/theme/statusStyles';
import type { MediaRequest } from '@/types';
import { formatDate, formatRuntime, getStatusIcon } from '@/utils/formatters';

interface MediaInfoProps {
  request: MediaRequest;
}

export const MediaInfo: React.FC<MediaInfoProps> = ({ request }) => {
  const isMovie = request.type === 'movie';
  const statusIcon = getStatusIcon(request.status);
  const statusStyle = requestStatusStyles[request.status];

  return (
    <Card p={{ base: 5, md: 6 }}>
      <Stack spacing={6}>
        <Box w="100%" display={{ base: 'block', md: 'none' }}>
          <AspectRatio ratio={2 / 3} w="100%">
            <Image
              src={request.poster_url}
              alt={`${request.title} poster`}
              borderRadius="lg"
              objectFit="cover"
              fallbackSrc="/logo192.png"
            />
          </AspectRatio>
        </Box>

        <Flex
          direction={{ base: 'column', md: 'row' }}
          gap={{ base: 6, md: 8 }}
          align={{ base: 'flex-start', md: 'stretch' }}
        >
          <Box display={{ base: 'none', md: 'block' }} flexShrink={0}>
            <Image
              src={request.poster_url}
              alt={`${request.title} poster`}
              borderRadius="lg"
              objectFit="cover"
              minW="240px"
              maxW="280px"
              height="360px"
              fallbackSrc="/logo192.png"
            />
          </Box>

          <Stack spacing={{ base: 5, md: 6 }} flex={1} minW={0}>
            <Flex
              direction={{ base: 'column', sm: 'row' }}
              align={{ base: 'flex-start', sm: 'flex-start' }}
              justify="space-between"
              gap={4}
              w="100%"
            >
              <Stack spacing={2} minW={0}>
                <Heading size={{ base: 'lg', md: 'lg' }}>{request.title}</Heading>
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
              </Stack>

              <Badge
                bg={statusStyle.bg}
                color={statusStyle.color}
                borderColor={statusStyle.borderColor}
                borderWidth="1px"
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

            <SimpleGrid columns={{ base: 2, md: 3 }} spacing={4}>
              <InfoItem label="Type">{isMovie ? '🎬 Movie' : '📺 TV Series'}</InfoItem>
              <InfoItem label="Created">{formatDate(request.created_at)}</InfoItem>
              <InfoItem label="Updated">{formatDate(request.updated_at)}</InfoItem>
              {!isMovie && (
                <InfoItem label="Series">
                  {request.series_title} ({request.series_year})
                </InfoItem>
              )}
              {!isMovie && <InfoItem label="Episodes">{request.total_episodes}</InfoItem>}
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
        </Flex>
      </Stack>
    </Card>
  );
};

interface InfoItemProps {
  label: string;
  children: React.ReactNode;
}

const InfoItem: React.FC<InfoItemProps> = ({ label, children }) => (
  <Box bg="bg.subtle" borderWidth="1px" borderColor="border.muted" borderRadius="lg" p={4}>
    <Text fontSize="xs" textTransform="uppercase" color="text.subtle" letterSpacing="0.08em">
      {label}
    </Text>
    <Text fontSize="sm" fontWeight="600" mt={2} color="slate.100">
      {children}
    </Text>
  </Box>
);
