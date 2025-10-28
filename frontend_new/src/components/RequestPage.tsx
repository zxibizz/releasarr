import {
  Box,
  Button,
  Card,
  Center,
  Flex,
  Heading,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalHeader,
  ModalOverlay,
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
import EpisodeMapping from "./EpisodeMapping";
import FileRequestMapping from "./FileRequestMapping";
import { MediaInfo } from "./MediaInfo";
import ReleasesList from "./ReleasesList";
import { TorrentSearch } from "./TorrentSearch";

export const RequestPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { request, loading, error } = useRequest(id || "");
  const [selectedRelease, setSelectedRelease] = useState<Release | null>(null);

  const filesModal = useDisclosure();
  const mappingModal = useDisclosure();

  const handleViewFiles = (release: Release) => {
    setSelectedRelease(release);
    filesModal.onOpen();
  };

  const handleEditMapping = (release: Release) => {
    setSelectedRelease(release);
    mappingModal.onOpen();
  };

  const closeModals = () => {
    filesModal.onClose();
    mappingModal.onClose();
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

      <TorrentSearch requestId={request.id} requestTitle={request.title} />

      <Card p={{ base: 5, md: 6 }}>
        <Stack spacing={4}>
          <Stack spacing={1}>
            <Heading size="md">📦 Releases</Heading>
            <Text color="text.subtle" fontSize="sm">
              Torrent releases associated with this request
            </Text>
          </Stack>

          <ReleasesList
            requestId={request.id}
            onViewFiles={handleViewFiles}
            onEditMapping={handleEditMapping}
          />
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

      <FilesModal
        isOpen={filesModal.isOpen}
        onClose={closeModals}
        release={selectedRelease}
      />

      <MappingModal
        isOpen={mappingModal.isOpen}
        onClose={closeModals}
        release={selectedRelease}
        requestType={request.type}
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

interface FilesModalProps {
  isOpen: boolean;
  onClose: () => void;
  release: Release | null;
}

const FilesModal: React.FC<FilesModalProps> = ({ isOpen, onClose, release }) => (
  <Modal isOpen={isOpen} onClose={onClose} size="6xl" scrollBehavior="inside">
    <ModalOverlay bg="rgba(0, 0, 0, 0.8)" backdropFilter="blur(6px)" />
    <ModalContent bg="bg.surface" borderWidth="1px" borderColor="border.muted">
      <ModalHeader>
        📁 Files
        {release ? ` in ${release.name}` : ""}
      </ModalHeader>
      <ModalCloseButton />
      <ModalBody>
        {release ? (
          <Stack spacing={4}>
            {release.files.map((file) => (
              <Card key={file.id} p={4} bg="bg.subtle" borderWidth="1px" borderColor="border.muted">
                <Stack spacing={3}>
                  <Flex align="flex-start" gap={3} wrap="wrap">
                    <Box flex={1} minW={0}>
                      <Text fontWeight="600" wordBreak="break-all">
                        {file.name}
                      </Text>
                      <Flex gap={4} fontSize="sm" color="text.subtle" mt={1}>
                        <Text>
                          Size: {(file.size / (1024 * 1024 * 1024)).toFixed(2)} GB
                        </Text>
                        <Text>Progress: 100%</Text>
                      </Flex>
                    </Box>
                  </Flex>

                  <ProgressSection title="Episode Mapping" color="blue.300">
                    {file.episode_mapping ? (
                      <Text fontSize="sm" color="blue.200">
                        📺 S{file.episode_mapping.season.toString().padStart(2, "0")}
                        E{file.episode_mapping.episode.toString().padStart(2, "0")}
                        {file.episode_mapping.title && ` - ${file.episode_mapping.title}`}
                      </Text>
                    ) : (
                      <Text fontSize="sm" color="text.subtle">
                        No episode mapping configured
                      </Text>
                    )}
                  </ProgressSection>

                  <ProgressSection title="Request Mapping" color="purple.300">
                    {file.request_mapping ? (
                      <Text fontSize="sm" color="purple.200">
                        🔗 {file.request_mapping.request_title || file.request_mapping.request_id}
                        {file.request_mapping.season && file.request_mapping.episode &&
                          ` - S${file.request_mapping.season.toString().padStart(2, "0")}E${file.request_mapping.episode
                            ?.toString()
                            .padStart(2, "0")}`}
                      </Text>
                    ) : (
                      <Text fontSize="sm" color="text.subtle">
                        No request mapping configured
                      </Text>
                    )}
                  </ProgressSection>
                </Stack>
              </Card>
            ))}
          </Stack>
        ) : (
          <Text color="text.subtle">No release selected.</Text>
        )}
      </ModalBody>
    </ModalContent>
  </Modal>
);

interface MappingModalProps {
  isOpen: boolean;
  onClose: () => void;
  release: Release | null;
  requestType: "movie" | "series";
}

const MappingModal: React.FC<MappingModalProps> = ({
  isOpen,
  onClose,
  release,
  requestType,
}) => {
  if (!release) return null;

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="6xl" scrollBehavior="inside">
      <ModalOverlay bg="rgba(0, 0, 0, 0.8)" backdropFilter="blur(6px)" />
      <ModalContent bg="bg.surface" borderWidth="1px" borderColor="border.muted">
        <ModalHeader>🗺️ Map Files{release ? ` - ${release.name}` : ""}</ModalHeader>
        <ModalCloseButton />
        <ModalBody pb={6} maxH="75vh" overflowY="auto">
          {release && requestType === "series" ? (
            <EpisodeMapping releaseId={release.id} files={release.files} onMappingUpdate={() => {}} />
          ) : release ? (
            <FileRequestMapping releaseId={release.id} files={release.files} onMappingUpdate={() => {}} />
          ) : (
            <Text color="text.subtle">No release selected.</Text>
          )}
        </ModalBody>
      </ModalContent>
    </Modal>
  );
};

interface ProgressSectionProps {
  title: string;
  color: string;
  children: React.ReactNode;
}

const ProgressSection: React.FC<ProgressSectionProps> = ({ title, color, children }) => (
  <Stack spacing={2}>
    <Text fontSize="xs" textTransform="uppercase" fontWeight="600" color={color}>
      {title}
    </Text>
    {children}
  </Stack>
);
