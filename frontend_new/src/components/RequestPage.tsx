import {
  Button,
  Card,
  Center,
  Heading,
  SimpleGrid,
  Spinner,
  Stack,
  Text,
  useDisclosure,
} from "@chakra-ui/react";
import React, { useState } from "react";
import { Link as RouterLink, useParams } from "react-router-dom";
import { useRequest } from "../hooks/useRequests";
import { Release } from "../types";
import { MediaInfo } from "./MediaInfo";
import ReleasesList from "./ReleasesList";
import { ReleaseSearch } from "./ReleaseSearch";
import ReleaseFilesModal from "./ReleaseFilesModal";

export const RequestPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { request, loading, error } = useRequest(id || "");
  const [selectedRelease, setSelectedRelease] = useState<Release | null>(null);

  const filesModal = useDisclosure();

  const handleViewFiles = (release: Release) => {
    setSelectedRelease(release);
    filesModal.onOpen();
  };

  const closeModal = () => {
    filesModal.onClose();
    setSelectedRelease(null);
  };

  if (loading) {
    return (
      <Center py={16} flexDirection="column" gap={4} color="text.subtle">
        <Spinner size="lg" color="brand.400" />
        <Text>Loading request...</Text>
      </Center>
    );
  }

  if (error || !request) {
    return (
      <Card p={8} maxW="lg" mx="auto">
        <Stack spacing={4} align="center">
          <Text fontSize="3xl">❌</Text>
          <Heading size="md">Request not found</Heading>
          <Text color="text.subtle" textAlign="center">
            {error || "The requested media could not be found."}
          </Text>
          <Button as={RouterLink} to="/" colorScheme="blue">
            ← Back to Requests
          </Button>
        </Stack>
      </Card>
    );
  }

  return (
    <Stack spacing={8} maxW="6xl" mx="auto">
      <Button as={RouterLink} to="/" variant="outline" colorScheme="blue" width="fit-content">
        ← Back to Requests
      </Button>

      <Stack spacing={2}>
        <Heading size="2xl">{request.title}</Heading>
        <Text color="text.subtle" fontSize="md">
          {request.type === "movie" ? "Movie" : "TV Series"} Request Details
        </Text>
      </Stack>

      <MediaInfo request={request} />

      <ReleaseSearch requestId={request.id} requestTitle={request.title} />

      <Card p={{ base: 5, md: 6 }}>
        <Stack spacing={4}>
          <Stack spacing={1}>
            <Heading size="md">📦 Releases</Heading>
            <Text color="text.subtle" fontSize="sm">
              Releases linked to this request
            </Text>
          </Stack>

          <ReleasesList requestId={request.id} onViewFiles={handleViewFiles} />
        </Stack>
      </Card>

      <Card p={{ base: 5, md: 6 }}>
        <Stack spacing={4}>
          <Heading size="md">🔧 Request Actions</Heading>
          <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4}>
            {actionCards.map((action) => (
              <Card
                key={action.title}
                p={4}
                bg="bg.subtle"
                borderWidth="1px"
                borderColor="border.muted"
                as={Button}
                variant="ghost"
                colorScheme="gray"
                textAlign="left"
                height="auto"
                flexDirection="column"
                alignItems="flex-start"
                onClick={() => alert(action.message)}
              >
                <Text fontSize="2xl" mb={2}>
                  {action.icon}
                </Text>
                <Text fontWeight="600" mb={1}>
                  {action.title}
                </Text>
                <Text fontSize="sm" color="text.subtle">
                  {action.description}
                </Text>
              </Card>
            ))}
          </SimpleGrid>
        </Stack>
      </Card>

      <ReleaseFilesModal
        isOpen={filesModal.isOpen}
        onClose={closeModal}
        release={selectedRelease}
        currentRequest={request}
      />
    </Stack>
  );
};

const actionCards = [
  {
    title: "Refresh Status",
    description: "Check for updates on this request",
    icon: "🔄",
    message: "Refresh functionality would be implemented here",
  },
  {
    title: "Manual Search",
    description: "Trigger a manual search for releases",
    icon: "🔍",
    message: "Manual search functionality would be implemented here",
  },
  {
    title: "View Logs",
    description: "Check processing logs for this request",
    icon: "📋",
    message: "View logs functionality would be implemented here",
  },
];
