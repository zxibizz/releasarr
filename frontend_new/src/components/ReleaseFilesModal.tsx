import {
  Card,
  Flex,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalHeader,
  ModalOverlay,
  Stack,
  Tab,
  TabList,
  TabPanel,
  TabPanels,
  Tabs,
  Text,
} from "@chakra-ui/react";
import React, { useCallback, useEffect, useMemo, useState } from "react";

import type {
  FileRequestMapping as FileRequestMappingType,
  MediaRequest,
  Release,
} from "@/types";

import FileRequestMapping from "./FileRequestMapping";

interface ReleaseFilesModalProps {
  isOpen: boolean;
  onClose: () => void;
  release: Release | null;
  currentRequest: MediaRequest;
}

const ReleaseFilesModal: React.FC<ReleaseFilesModalProps> = ({
  isOpen,
  onClose,
  release,
  currentRequest,
}) => {
  const [localRelease, setLocalRelease] = useState<Release | null>(release);

  useEffect(() => {
    if (!release) {
      setLocalRelease(null);
      return;
    }

    setLocalRelease((prev) => {
      if (!prev || prev.id !== release.id) {
        return release;
      }
      return prev;
    });
  }, [release]);

  const defaultMappingRequest = useMemo(
    () => ({
      id: currentRequest.id,
      title: currentRequest.title,
      type: currentRequest.type,
      season_number:
        currentRequest.type === "series"
          ? currentRequest.season_number
          : undefined,
    }),
    [currentRequest]
  );

  const activeRelease = localRelease;

  const handleMappingUpdate = useCallback(
    (fileId: string, mapping: FileRequestMappingType) => {
      setLocalRelease((prev) => {
        if (!prev) {
          return prev;
        }

        return {
          ...prev,
          files: prev.files.map((file) =>
            file.id === fileId
              ? {
                  ...file,
                  request_mapping: mapping,
                }
              : file
          ),
        };
      });
    },
    []
  );

  if (!activeRelease) return null;

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="6xl" scrollBehavior="inside">
      <ModalOverlay bg="rgba(0, 0, 0, 0.8)" backdropFilter="blur(6px)" />
      <ModalContent
        bg="bg.surface"
        borderWidth="1px"
        borderColor="border.muted"
      >
        <ModalHeader>📁 Files — {activeRelease.name}</ModalHeader>
        <ModalCloseButton />
        <ModalBody pb={6} maxH="75vh" overflowY="auto">
          <Tabs colorScheme="blue">
            <TabList>
              <Tab>Files</Tab>
              <Tab>Mapping</Tab>
            </TabList>
            <TabPanels mt={4}>
              <TabPanel px={0}>
                <Stack spacing={4}>
                  {activeRelease.files.map((file) => {
                    const requestMappingSummary = file.request_mapping
                      ? `${
                          file.request_mapping.request_title ||
                          file.request_mapping.request_id
                        } (${
                          file.request_mapping.mapping_type === "series"
                            ? "Series"
                            : "Movie"
                        })`
                      : "Not mapped";
                    const seriesMappingSummary =
                      file.request_mapping?.mapping_type === "series" &&
                      typeof file.request_mapping.season === "number" &&
                      typeof file.request_mapping.episode === "number"
                        ? `S${file.request_mapping.season
                            .toString()
                            .padStart(2, "0")}E${file.request_mapping.episode
                            .toString()
                            .padStart(2, "0")}`
                        : "Not mapped";

                    return (
                      <Card
                        key={file.id}
                        p={4}
                        bg="bg.subtle"
                        borderWidth="1px"
                        borderColor="border.muted"
                      >
                        <Stack spacing={3}>
                          <Flex align="flex-start" gap={3} wrap="wrap">
                            <Stack spacing={1} flex={1} minW={0}>
                              <Text fontWeight="600" wordBreak="break-all">
                                {file.name}
                              </Text>
                              <Flex gap={4} fontSize="sm" color="text.subtle">
                                <Text>
                                  Size:{" "}
                                  {(file.size / (1024 * 1024 * 1024)).toFixed(
                                    2
                                  )}{" "}
                                  GB
                                </Text>
                                <Text>Progress: 100%</Text>
                              </Flex>
                            </Stack>
                          </Flex>

                          <Stack spacing={2}>
                            <Text
                              fontSize="xs"
                              textTransform="uppercase"
                              fontWeight="600"
                              color="text.subtle"
                            >
                              Mapping
                            </Text>
                            <Stack
                              spacing={1}
                              fontSize="sm"
                              color="text.subtle"
                            >
                              <Text>Request: {requestMappingSummary}</Text>
                              <Text>Episode: {seriesMappingSummary}</Text>
                            </Stack>
                          </Stack>
                        </Stack>
                      </Card>
                    );
                  })}
                </Stack>
              </TabPanel>

              <TabPanel px={0}>
                <FileRequestMapping
                  releaseId={activeRelease.id}
                  files={activeRelease.files}
                  onMappingUpdate={handleMappingUpdate}
                  defaultRequest={defaultMappingRequest}
                />
              </TabPanel>
            </TabPanels>
          </Tabs>
        </ModalBody>
      </ModalContent>
    </Modal>
  );
};

export default ReleaseFilesModal;
