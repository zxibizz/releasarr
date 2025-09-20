import {
  Alert,
  AlertDescription,
  AlertIcon,
  Box,
  Button,
  Checkbox,
  Flex,
  Grid,
  Heading,
  Input,
  Select,
  Stack,
  Tag,
  Text,
  VStack,
} from "@chakra-ui/react";
import React, { useEffect, useMemo, useState } from "react";
import { useReleaseFileMapping } from "../hooks/useReleases";
import { useRequests } from "../hooks/useRequests";
import {
  FileRequestMapping as FileRequestMappingType,
  ReleaseFile,
} from "../types";
import {
  formatFileSize,
  groupFilesByType,
  isVideoFile,
  validateRequestMapping,
} from "../utils/releaseHelpers";

interface FileRequestMappingProps {
  releaseId: string;
  files: ReleaseFile[];
  onMappingUpdate?: (fileId: string, mapping: FileRequestMappingType) => void;
  onClose?: () => void;
  readonly?: boolean;
}

interface FileMapping {
  fileId: string;
  requestId: string;
  requestTitle: string;
  mappingType: "episode" | "movie" | "season";
  season?: number;
  episode?: number;
}

const FileRequestMapping: React.FC<FileRequestMappingProps> = ({
  releaseId,
  files,
  onMappingUpdate,
  readonly = false,
}) => {
  const { updateFileMapping, loading, error } = useReleaseFileMapping();
  const { requests } = useRequests();
  const [mappings, setMappings] = useState<FileMapping[]>([]);
  const [showOnlyVideo, setShowOnlyVideo] = useState(true);
  const [selectedRequest, setSelectedRequest] = useState<string>("");

  const groupedFiles = useMemo(() => groupFilesByType(files), [files]);
  const { video, subtitle, other } = groupedFiles;
  const displayFiles = useMemo(
    () => (showOnlyVideo ? video : files),
    [showOnlyVideo, video, files]
  );

  useEffect(() => {
    const sourceFiles = showOnlyVideo ? video : files;
    const initialMappings = sourceFiles.map((file) => {
      const existing = file.request_mapping;

      return {
        fileId: file.id,
        requestId: existing?.request_id || "",
        requestTitle: existing?.request_title || "",
        mappingType: existing?.mapping_type || "movie",
        season: existing?.season,
        episode: existing?.episode,
      };
    });

    setMappings(initialMappings);
  }, [files, video, showOnlyVideo]);

  const availableRequests = useMemo(
    () => requests.filter((request) => request.status !== "failed"),
    [requests]
  );

  const movieRequests = useMemo(
    () => availableRequests.filter((request) => request.type === "movie"),
    [availableRequests]
  );

  const seriesRequests = useMemo(
    () => availableRequests.filter((request) => request.type === "series"),
    [availableRequests]
  );

  const handleMappingChange = (
    fileId: string,
    field: keyof Omit<FileMapping, "fileId">,
    value: string | number | undefined
  ) => {
    setMappings((prev) =>
      prev.map((mapping) => {
        if (mapping.fileId !== fileId) return mapping;

        const updated: FileMapping = { ...mapping, [field]: value } as FileMapping;

        if (field === "requestId" && typeof value === "string") {
          const request = requests.find((r) => r.id === value);
          updated.requestTitle = request?.title || "";
          if (request) {
            updated.mappingType = request.type === "series" ? "episode" : "movie";
          }
        }

        if (field === "mappingType" && value !== "season") {
          updated.season = undefined;
        }

        return updated;
      })
    );
  };

  const handleSaveMapping = async (fileId: string) => {
    const mapping = mappings.find((m) => m.fileId === fileId);
    if (!mapping || !mapping.requestId) return;

    const requestMapping: FileRequestMappingType = {
      request_id: mapping.requestId,
      request_title: mapping.requestTitle,
      mapping_type: mapping.mappingType,
      season: mapping.season,
      episode: mapping.episode,
    };

    if (!validateRequestMapping(requestMapping)) {
      alert("Invalid request mapping. Please check all required fields.");
      return;
    }

    try {
      await updateFileMapping(releaseId, fileId, {
        request_mapping: requestMapping,
      });
      onMappingUpdate?.(fileId, requestMapping);
    } catch (err) {
      console.error("Failed to update mapping:", err);
    }
  };

  const handleSaveAllMappings = async () => {
    for (const mapping of mappings) {
      if (!mapping.requestId) continue;

      const requestMapping: FileRequestMappingType = {
        request_id: mapping.requestId,
        request_title: mapping.requestTitle,
        mapping_type: mapping.mappingType,
        season: mapping.season,
        episode: mapping.episode,
      };

      if (validateRequestMapping(requestMapping)) {
        try {
          await updateFileMapping(releaseId, mapping.fileId, {
            request_mapping: requestMapping,
          });
          onMappingUpdate?.(mapping.fileId, requestMapping);
        } catch (err) {
          console.error(`Failed to update mapping for ${mapping.fileId}:`, err);
        }
      }
    }
  };

  const handleBulkRequestUpdate = (requestId: string) => {
    const request = requests.find((r) => r.id === requestId);
    if (!request) return;

    setMappings((prev) =>
      prev.map((mapping) => ({
        ...mapping,
        requestId,
        requestTitle: request.title,
        mappingType: request.type === "series" ? "episode" : "movie",
      }))
    );
  };

  const handleClearMapping = (fileId: string) => {
    setMappings((prev) =>
      prev.map((mapping) =>
        mapping.fileId === fileId
          ? {
              ...mapping,
              requestId: "",
              requestTitle: "",
              mappingType: "movie",
              season: undefined,
              episode: undefined,
            }
          : mapping
      )
    );
  };

  const getFileMapping = (fileId: string) => mappings.find((m) => m.fileId === fileId);

  const getExistingMapping = (fileId: string) =>
    files.find((f) => f.id === fileId)?.request_mapping;

  const hasChanges = (fileId: string) => {
    const current = getFileMapping(fileId);
    const existing = getExistingMapping(fileId);

    if (!current) return false;
    if (!existing && !current.requestId) return false;
    if (!existing && current.requestId) return true;

    return (
      current.requestId !== (existing?.request_id || "") ||
      current.requestTitle !== (existing?.request_title || "") ||
      current.mappingType !== (existing?.mapping_type || "movie") ||
      current.season !== existing?.season ||
      current.episode !== existing?.episode
    );
  };

  return (
    <Stack spacing={6}>
      <Stack spacing={1}>
        <Heading size="md">🔗 File Request Mapping</Heading>
        <Text fontSize="sm" color="text.subtle">
          Map release files to other requests to manage shared content.
        </Text>
      </Stack>

      {!readonly && (
        <Stack spacing={4}>
          <Flex gap={4} wrap="wrap">
            <Checkbox
              isChecked={showOnlyVideo}
              onChange={(e) => setShowOnlyVideo(e.target.checked)}
              colorScheme="blue"
            >
              Show only video files ({video.length})
            </Checkbox>
          </Flex>

          <Flex align={{ base: "flex-start", md: "center" }} direction={{ base: "column", md: "row" }} gap={3} wrap="wrap">
            <Text fontWeight="600" fontSize="sm">
              Bulk assign to request:
            </Text>
            <Select
              placeholder="Select a request..."
              value={selectedRequest}
              onChange={(e) => {
                setSelectedRequest(e.target.value);
                if (e.target.value) {
                  handleBulkRequestUpdate(e.target.value);
                }
              }}
              maxW="320px"
              size="sm"
            >
              {movieRequests.length > 0 && (
                <optgroup label="Movies">
                  {movieRequests.map((request) => (
                    <option key={request.id} value={request.id}>
                      {request.title} ({request.year})
                    </option>
                  ))}
                </optgroup>
              )}
              {seriesRequests.length > 0 && (
                <optgroup label="Series">
                  {seriesRequests.map((request) => (
                    <option key={request.id} value={request.id}>
                      {request.title} ({request.year})
                    </option>
                  ))}
                </optgroup>
              )}
            </Select>
          </Flex>
        </Stack>
      )}

      {error && (
        <Alert status="error" borderRadius="md" alignItems="flex-start">
          <AlertIcon />
          <AlertDescription fontSize="sm">{error}</AlertDescription>
        </Alert>
      )}

      <Stack spacing={4}>
        {displayFiles.length === 0 ? (
          <VStack
            spacing={3}
            py={12}
            bg="bg.subtle"
            borderRadius="xl"
            borderWidth="1px"
            borderColor="border.muted"
          >
            <Text fontSize="3xl">📁</Text>
            <Heading size="sm">No files to map</Heading>
            <Text fontSize="sm" color="text.subtle" textAlign="center">
              No {showOnlyVideo ? "video " : ""}files available for mapping.
            </Text>
          </VStack>
        ) : (
          displayFiles.map((file) => {
            const mapping = getFileMapping(file.id);
            const existing = getExistingMapping(file.id);
            const changed = hasChanges(file.id);

            return (
              <Box
                key={file.id}
                borderWidth="1px"
                borderRadius="lg"
                borderColor={existing ? "blue.400" : "border.muted"}
                bg={existing ? "rgba(59, 130, 246, 0.14)" : "bg.subtle"}
                p={4}
              >
                <Stack spacing={3}>
                  <Flex align="center" gap={3} wrap="wrap">
                    <Text fontSize="lg">{isVideoFile(file.name) ? "🎬" : "📄"}</Text>
                    <Text fontWeight="600" noOfLines={1} flex={1} minW={0}>
                      {file.name}
                    </Text>
                    <Text fontSize="xs" color="text.subtle">
                      ({formatFileSize(file.size)})
                    </Text>
                    {existing && (
                      <Tag colorScheme="blue" variant="subtle" size="sm">
                        Mapped
                      </Tag>
                    )}
                    {changed && (
                      <Tag colorScheme="yellow" variant="subtle" size="sm">
                        Changed
                      </Tag>
                    )}
                  </Flex>

                  {existing && (
                    <Text fontSize="sm" color="text.subtle">
                      Current: {existing.request_title} ({existing.mapping_type})
                      {existing.season && existing.episode &&
                        ` - S${existing.season.toString().padStart(2, "0")}E${existing.episode
                          .toString()
                          .padStart(2, "0")}`}
                    </Text>
                  )}

                  {!readonly && mapping && (
                    <Stack spacing={3}>
                      <Grid templateColumns={{ base: "repeat(1, minmax(0, 1fr))", md: "repeat(2, minmax(0, 1fr))" }} gap={3}>
                        <Box>
                          <Text fontSize="xs" fontWeight="600" textTransform="uppercase" color="text.subtle">
                            Request
                          </Text>
                          <Select
                            placeholder="Select request..."
                            value={mapping.requestId}
                            size="sm"
                            onChange={(e) =>
                              handleMappingChange(file.id, "requestId", e.target.value)
                            }
                          >
                            {movieRequests.length > 0 && (
                              <optgroup label="Movies">
                                {movieRequests.map((request) => (
                                  <option key={request.id} value={request.id}>
                                    {request.title} ({request.year})
                                  </option>
                                ))}
                              </optgroup>
                            )}
                            {seriesRequests.length > 0 && (
                              <optgroup label="Series">
                                {seriesRequests.map((request) => (
                                  <option key={request.id} value={request.id}>
                                    {request.title} ({request.year})
                                  </option>
                                ))}
                              </optgroup>
                            )}
                          </Select>
                        </Box>

                        <Box>
                          <Text fontSize="xs" fontWeight="600" textTransform="uppercase" color="text.subtle">
                            Mapping Type
                          </Text>
                          <Select
                            value={mapping.mappingType}
                            size="sm"
                            onChange={(e) =>
                              handleMappingChange(file.id, "mappingType", e.target.value as FileMapping["mappingType"])
                            }
                          >
                            <option value="movie">Movie</option>
                            <option value="season">Season</option>
                            <option value="episode">Episode</option>
                          </Select>
                        </Box>
                      </Grid>

                      {mapping.mappingType === "season" && (
                        <Box>
                          <Text fontSize="xs" fontWeight="600" textTransform="uppercase" color="text.subtle">
                            Season
                          </Text>
                          <Input
                            type="number"
                            min={1}
                            max={99}
                            value={mapping.season ?? 1}
                            size="sm"
                            onChange={(e) =>
                              handleMappingChange(
                                file.id,
                                "season",
                                e.target.value ? parseInt(e.target.value, 10) : 1
                              )
                            }
                          />
                        </Box>
                      )}

                      {mapping.mappingType === "episode" && (
                        <Grid templateColumns="repeat(2, minmax(0, 1fr))" gap={3}>
                          <Box>
                            <Text fontSize="xs" fontWeight="600" textTransform="uppercase" color="text.subtle">
                              Season
                            </Text>
                            <Input
                              type="number"
                              min={1}
                              max={99}
                              value={mapping.season ?? 1}
                              size="sm"
                              onChange={(e) =>
                                handleMappingChange(
                                  file.id,
                                  "season",
                                  e.target.value ? parseInt(e.target.value, 10) : 1
                                )
                              }
                            />
                          </Box>
                          <Box>
                            <Text fontSize="xs" fontWeight="600" textTransform="uppercase" color="text.subtle">
                              Episode
                            </Text>
                            <Input
                              type="number"
                              min={1}
                              max={999}
                              value={mapping.episode ?? 1}
                              size="sm"
                              onChange={(e) =>
                                handleMappingChange(
                                  file.id,
                                  "episode",
                                  e.target.value ? parseInt(e.target.value, 10) : 1
                                )
                              }
                            />
                          </Box>
                        </Grid>
                      )}
                    </Stack>
                  )}

                  {readonly && existing && (
                    <Text fontSize="sm" color="slate.100">
                      {existing.request_title} ({existing.mapping_type})
                      {existing.season && existing.episode &&
                        ` - S${existing.season.toString().padStart(2, "0")}E${existing.episode
                          .toString()
                          .padStart(2, "0")}`}
                    </Text>
                  )}

                  {!readonly && (
                    <Flex gap={2} justify="flex-end" flexWrap="wrap">
                      <Button
                        size="sm"
                        colorScheme="blue"
                        variant={changed && mapping?.requestId ? "solid" : "outline"}
                        onClick={() => handleSaveMapping(file.id)}
                        isDisabled={loading || !changed || !mapping?.requestId}
                      >
                        {loading ? "Saving..." : "Save"}
                      </Button>
                      {mapping?.requestId && (
                        <Button
                          size="sm"
                          colorScheme="red"
                          variant="outline"
                          onClick={() => handleClearMapping(file.id)}
                        >
                          Clear
                        </Button>
                      )}
                    </Flex>
                  )}
                </Stack>
              </Box>
            );
          })
        )}
      </Stack>

      {!readonly && displayFiles.length > 0 && (
        <Flex
          direction={{ base: "column", md: "row" }}
          justify="space-between"
          align={{ base: "flex-start", md: "center" }}
          gap={3}
          pt={4}
          borderTopWidth="1px"
          borderTopColor="border.muted"
        >
          <Text fontSize="sm" color="text.subtle">
            {mappings.filter((m) => hasChanges(m.fileId)).length} unsaved changes
          </Text>
          <Button
            onClick={handleSaveAllMappings}
            size="sm"
            colorScheme="blue"
            variant={mappings.some((m) => hasChanges(m.fileId)) ? "solid" : "outline"}
            isDisabled={loading || !mappings.some((m) => hasChanges(m.fileId))}
          >
            {loading ? "Saving All..." : "Save All Changes"}
          </Button>
        </Flex>
      )}

      {!showOnlyVideo && (
        <Text fontSize="sm" color="text.subtle">
          File types: {video.length} video, {subtitle.length} subtitle,{" "}
          {other.length} other
        </Text>
      )}

      <Text fontSize="sm" color="text.subtle">
        Available requests: {movieRequests.length} movies, {seriesRequests.length} series
      </Text>
    </Stack>
  );
};

export default FileRequestMapping;
