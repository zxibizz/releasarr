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
  Stack,
  Tag,
  Text,
  VStack,
} from "@chakra-ui/react";
import React, { useEffect, useState } from "react";
import { useReleaseFileMapping } from "../hooks/useReleases";
import { EpisodeMapping as EpisodeMappingType, ReleaseFile } from "../types";
import {
  formatEpisodeString,
  formatEpisodeTitle,
  groupFilesByType,
  isVideoFile,
  suggestEpisodeMapping,
  validateEpisodeMapping,
} from "../utils/releaseHelpers";

interface EpisodeMappingProps {
  releaseId: string;
  files: ReleaseFile[];
  onMappingUpdate?: (fileId: string, mapping: EpisodeMappingType) => void;
  onClose?: () => void;
  readonly?: boolean;
}

interface FileMapping {
  fileId: string;
  season: number;
  episode: number;
  title: string;
}

const EpisodeMapping: React.FC<EpisodeMappingProps> = ({
  releaseId,
  files,
  onMappingUpdate,
  readonly = false,
}) => {
  const { updateFileMapping, loading, error } = useReleaseFileMapping();
  const [mappings, setMappings] = useState<FileMapping[]>([]);
  const [autoSuggest, setAutoSuggest] = useState(true);
  const [showOnlyVideo, setShowOnlyVideo] = useState(true);

  const { video, subtitle, other } = groupFilesByType(files);
  const displayFiles = showOnlyVideo ? video : files;

  useEffect(() => {
    const initialMappings = displayFiles.map((file) => {
      const existing = file.episode_mapping;
      const suggested = autoSuggest ? suggestEpisodeMapping(file) : null;
      const mapping = existing || suggested;

      return {
        fileId: file.id,
        season: mapping?.season || 1,
        episode: mapping?.episode || 1,
        title: mapping?.title || "",
      };
    });

    setMappings(initialMappings);
  }, [displayFiles, autoSuggest]);

  const handleMappingChange = (
    fileId: string,
    field: keyof Omit<FileMapping, "fileId">,
    value: string | number
  ) => {
    setMappings((prev) =>
      prev.map((mapping) =>
        mapping.fileId === fileId ? { ...mapping, [field]: value } : mapping
      )
    );
  };

  const handleSaveMapping = async (fileId: string) => {
    const mapping = mappings.find((m) => m.fileId === fileId);
    if (!mapping) return;

    const episodeMapping: EpisodeMappingType = {
      season: mapping.season,
      episode: mapping.episode,
      title: mapping.title || undefined,
    };

    if (!validateEpisodeMapping(episodeMapping)) {
      alert("Invalid episode mapping. Please check season and episode numbers.");
      return;
    }

    try {
      await updateFileMapping(releaseId, fileId, {
        episode_mapping: episodeMapping,
      });
      onMappingUpdate?.(fileId, episodeMapping);
    } catch (err) {
      console.error("Failed to update mapping:", err);
    }
  };

  const handleSaveAllMappings = async () => {
    for (const mapping of mappings) {
      const episodeMapping: EpisodeMappingType = {
        season: mapping.season,
        episode: mapping.episode,
        title: mapping.title || undefined,
      };

      if (validateEpisodeMapping(episodeMapping)) {
        try {
          await updateFileMapping(releaseId, mapping.fileId, {
            episode_mapping: episodeMapping,
          });
          onMappingUpdate?.(mapping.fileId, episodeMapping);
        } catch (err) {
          console.error(`Failed to update mapping for ${mapping.fileId}:`, err);
        }
      }
    }
  };

  const handleAutoSuggest = () => {
    const updatedMappings = displayFiles.map((file) => {
      const existing = mappings.find((m) => m.fileId === file.id);
      const suggested = suggestEpisodeMapping(file);

      return {
        fileId: file.id,
        season: suggested?.season || existing?.season || 1,
        episode: suggested?.episode || existing?.episode || 1,
        title: suggested?.title || existing?.title || "",
      };
    });

    setMappings(updatedMappings);
  };

  const handleBulkSeasonUpdate = (season: number) => {
    setMappings((prev) => prev.map((mapping) => ({ ...mapping, season })));
  };

  const getFileMapping = (fileId: string) => mappings.find((m) => m.fileId === fileId);

  const getExistingMapping = (fileId: string) => {
    const file = files.find((f) => f.id === fileId);
    return file?.episode_mapping;
  };

  const hasChanges = (fileId: string) => {
    const current = getFileMapping(fileId);
    const existing = getExistingMapping(fileId);

    if (!current) return false;
    if (!existing) return true;

    return (
      current.season !== existing.season ||
      current.episode !== existing.episode ||
      current.title !== (existing.title || "")
    );
  };

  return (
    <Stack spacing={6}>
      <Stack spacing={1}>
        <Heading size="md">📺 Episode Mapping</Heading>
        <Text fontSize="sm" color="text.subtle">
          Map release files to specific episodes for series content.
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
            <Checkbox
              isChecked={autoSuggest}
              onChange={(e) => setAutoSuggest(e.target.checked)}
              colorScheme="blue"
            >
              Auto-suggest from filenames
            </Checkbox>
            <Button
              variant="outline"
              colorScheme="gray"
              size="sm"
              onClick={handleAutoSuggest}
            >
              Re-suggest All
            </Button>
          </Flex>

          <Flex align="center" gap={3} wrap="wrap">
            <Text fontWeight="600" fontSize="sm">
              Bulk set season:
            </Text>
            <Flex gap={2}>
              {[1, 2, 3, 4, 5].map((season) => (
                <Button
                  key={season}
                  variant="outline"
                  colorScheme="gray"
                  size="xs"
                  onClick={() => handleBulkSeasonUpdate(season)}
                >
                  S{season.toString().padStart(2, "0")}
                </Button>
              ))}
            </Flex>
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
                borderColor={existing ? "green.400" : "border.muted"}
                bg={existing ? "rgba(34, 197, 94, 0.12)" : "bg.subtle"}
                p={4}
              >
                <Stack spacing={3}>
                  <Flex align="center" gap={3} wrap="wrap">
                    <Text fontSize="lg">{isVideoFile(file.name) ? "🎬" : "📄"}</Text>
                    <Text fontWeight="600" noOfLines={1} flex={1} minW={0}>
                      {file.name}
                    </Text>
                    {existing && (
                      <Tag colorScheme="green" variant="subtle" size="sm">
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
                      Current: {formatEpisodeTitle(existing)}
                    </Text>
                  )}

                  {!readonly && mapping && (
                    <Grid templateColumns={{ base: "repeat(1, minmax(0, 1fr))", md: "repeat(3, minmax(0, 1fr))" }} gap={3}>
                      <Box>
                        <Text fontSize="xs" fontWeight="600" textTransform="uppercase" color="text.subtle">
                          Season
                        </Text>
                        <Input
                          type="number"
                          min={1}
                          max={99}
                          value={mapping.season}
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
                          value={mapping.episode}
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

                      <Box>
                        <Text fontSize="xs" fontWeight="600" textTransform="uppercase" color="text.subtle">
                          Title (optional)
                        </Text>
                        <Input
                          value={mapping.title}
                          placeholder="Episode title"
                          size="sm"
                          onChange={(e) => handleMappingChange(file.id, "title", e.target.value)}
                        />
                      </Box>
                    </Grid>
                  )}

                  {readonly && existing && (
                    <Text fontSize="sm" color="slate.100">
                      {formatEpisodeTitle(existing)}
                    </Text>
                  )}

                  {mapping && (
                    <Text fontSize="xs" color="text.subtle">
                      Preview: {formatEpisodeString(mapping)}
                      {mapping.title && ` - ${mapping.title}`}
                    </Text>
                  )}

                  {!readonly && (
                    <Flex justify="flex-end">
                      <Button
                        size="sm"
                        colorScheme="blue"
                        variant={changed ? "solid" : "outline"}
                        onClick={() => handleSaveMapping(file.id)}
                        isDisabled={loading || !changed}
                      >
                        {loading ? "Saving..." : "Save"}
                      </Button>
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
    </Stack>
  );
};

export default EpisodeMapping;
