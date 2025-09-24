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
  Spinner,
  Stack,
  Tag,
  Text,
  VStack,
  useToast,
} from '@chakra-ui/react';
import React, { useEffect, useMemo, useState } from 'react';

import { useReleaseFileMapping } from '@/hooks/useReleases';
import { useRequestsList } from '@/hooks/useRequests';
import type {
  FileRequestMapping as FileRequestMappingType,
  ReleaseFile,
  SeriesRequest,
} from '@/types';
import {
  formatFileSize,
  groupFilesByType,
  isVideoFile,
  parseSeriesEpisodeFromFilename,
  validateRequestMapping,
} from '@/utils/releaseHelpers';

interface FileRequestMappingProps {
  releaseId: string;
  files: ReleaseFile[];
  onMappingUpdate?: (_fileId: string, _mapping: FileRequestMappingType) => void;
  onClose?: () => void;
  readonly?: boolean;
  defaultRequest?: {
    id: string;
    title: string;
    type: 'movie' | 'series';
    season_number?: number;
  };
}

interface FileMapping {
  fileId: string;
  requestId: string;
  requestTitle: string;
  mappingType: 'movie' | 'series';
  season?: number;
  episode?: number;
}

const FileRequestMapping: React.FC<FileRequestMappingProps> = ({
  releaseId,
  files,
  onMappingUpdate,
  readonly = false,
  defaultRequest,
}) => {
  const { updateFileMappings, loading: isSaving, error: mappingError } = useReleaseFileMapping();
  const {
    requests,
    isLoading: requestsLoading,
    isFetching: isRequestsFetching,
    error: requestsError,
    refetch: refetchRequests,
  } = useRequestsList(undefined, { staleTime: 5 * 60_000 });
  const requestsErrorMessage =
    requestsError instanceof Error
      ? requestsError.message
      : requestsError
        ? 'Failed to load requests'
        : null;

  const showRequestsLoading = (requestsLoading || isRequestsFetching) && requests.length === 0;

  const toast = useToast();
  const [mappings, setMappings] = useState<FileMapping[]>([]);
  const [showOnlyVideo, setShowOnlyVideo] = useState(true);
  const [selectedRequest, setSelectedRequest] = useState<string>(defaultRequest?.id ?? '');

  const groupedFiles = useMemo(() => groupFilesByType(files), [files]);
  const { video, subtitle, other } = groupedFiles;
  const displayFiles = useMemo(
    () => (showOnlyVideo ? video : files),
    [showOnlyVideo, video, files],
  );

  useEffect(() => {
    const sourceFiles = showOnlyVideo ? video : files;
    const initialMappings = sourceFiles.map((file) => {
      const existing = file.request_mapping;
      if (existing) {
        if (existing.mapping_type === 'series') {
          return {
            fileId: file.id,
            requestId: existing.request_id,
            requestTitle: existing.request_title,
            mappingType: 'series',
            season: existing.season,
            episode: existing.episode,
          } as FileMapping;
        }

        return {
          fileId: file.id,
          requestId: existing.request_id,
          requestTitle: existing.request_title,
          mappingType: 'movie',
          season: undefined,
          episode: undefined,
        } as FileMapping;
      }

      const fallbackType: FileMapping['mappingType'] =
        defaultRequest && defaultRequest.type === 'series' ? 'series' : 'movie';
      const inferredEpisode = parseSeriesEpisodeFromFilename(file.name);
      const fallbackSeason =
        fallbackType === 'series'
          ? (defaultRequest?.season_number ?? inferredEpisode?.season ?? 1)
          : undefined;
      const fallbackEpisode =
        fallbackType === 'series' ? (inferredEpisode?.episode ?? 1) : undefined;

      const fallbackMapping: FileMapping =
        fallbackType === 'series'
          ? {
              fileId: file.id,
              requestId: defaultRequest?.id ?? '',
              requestTitle: defaultRequest?.title ?? '',
              mappingType: 'series',
              season: fallbackSeason,
              episode: fallbackEpisode,
            }
          : {
              fileId: file.id,
              requestId: defaultRequest?.id ?? '',
              requestTitle: defaultRequest?.title ?? '',
              mappingType: 'movie',
            };

      return fallbackMapping;
    });

    setMappings(initialMappings);
  }, [files, video, showOnlyVideo, defaultRequest]);

  useEffect(() => {
    if (defaultRequest?.id && !selectedRequest) {
      setSelectedRequest(defaultRequest.id);
    }
  }, [defaultRequest?.id, selectedRequest]);

  const availableRequests = useMemo(
    () => requests.filter((request) => request.status !== 'failed'),
    [requests],
  );

  const movieRequests = useMemo(
    () => availableRequests.filter((request) => request.type === 'movie'),
    [availableRequests],
  );

  const seriesRequests = useMemo(
    () => availableRequests.filter((request) => request.type === 'series'),
    [availableRequests],
  );

  const disableRequestSelection =
    showRequestsLoading || Boolean(requestsErrorMessage) || availableRequests.length === 0;

  const requestPlaceholder = showRequestsLoading
    ? 'Loading requests...'
    : requestsErrorMessage
      ? 'Unable to load requests'
      : 'Select a request...';

  const handleMappingChange = (
    fileId: string,
    field: keyof Omit<FileMapping, 'fileId'>,
    value: string | number | undefined,
  ) => {
    setMappings((prev) =>
      prev.map((mapping) => {
        if (mapping.fileId !== fileId) return mapping;

        const updated: FileMapping = {
          ...mapping,
          [field]: value,
        } as FileMapping;

        if (field === 'requestId' && typeof value === 'string') {
          const request = requests.find((r) => r.id === value);
          updated.requestTitle = request?.title || '';
          if (request) {
            updated.mappingType = request.type === 'series' ? 'series' : 'movie';
            if (updated.mappingType === 'movie') {
              updated.season = undefined;
              updated.episode = undefined;
            } else {
              updated.season = updated.season ?? 1;
              updated.episode = updated.episode ?? 1;
            }
          }
        }

        if (field === 'mappingType') {
          const type = value as FileMapping['mappingType'];
          if (type === 'movie') {
            updated.season = undefined;
            updated.episode = undefined;
          } else {
            updated.season = updated.season ?? 1;
            updated.episode = updated.episode ?? 1;
          }
        }

        return updated;
      }),
    );
  };

  const handleSaveMapping = async (fileId: string) => {
    const mapping = mappings.find((m) => m.fileId === fileId);
    if (!mapping || !mapping.requestId) return;

    let requestMappingPayload: FileRequestMappingType;
    if (mapping.mappingType === 'series') {
      requestMappingPayload = {
        request_id: mapping.requestId,
        mapping_type: 'series',
        season: mapping.season ?? 1,
        episode: mapping.episode ?? 1,
      };
    } else {
      requestMappingPayload = {
        request_id: mapping.requestId,
        mapping_type: 'movie',
      };
    }

    if (!validateRequestMapping(requestMappingPayload)) {
      toast({
        title: 'Invalid mapping',
        description: 'Please fill in all required fields before saving.',
        status: 'warning',
        duration: 4000,
        isClosable: true,
      });
      return;
    }

    const requestMappingForState: FileRequestMappingType = {
      ...requestMappingPayload,
      request_title: mapping.requestTitle,
    };

    try {
      await updateFileMappings(releaseId, [
        {
          file_id: fileId,
          request_mapping: requestMappingPayload,
        },
      ]);
      onMappingUpdate?.(fileId, requestMappingForState);
    } catch (err) {
      console.error('Failed to update mapping:', err);
    }
  };

  const handleSaveAllMappings = async () => {
    const preparedMappings = mappings.reduce<
      {
        fileId: string;
        payload: FileRequestMappingType;
        stateMapping: FileRequestMappingType;
      }[]
    >((acc, mapping) => {
      if (!mapping.requestId) {
        return acc;
      }

      let requestMappingPayload: FileRequestMappingType;
      if (mapping.mappingType === 'series') {
        requestMappingPayload = {
          request_id: mapping.requestId,
          mapping_type: 'series',
          season: mapping.season ?? 1,
          episode: mapping.episode ?? 1,
        };
      } else {
        requestMappingPayload = {
          request_id: mapping.requestId,
          mapping_type: 'movie',
        };
      }

      if (!validateRequestMapping(requestMappingPayload)) {
        return acc;
      }

      const stateMapping: FileRequestMappingType = {
        ...requestMappingPayload,
        request_title: mapping.requestTitle,
      };

      acc.push({
        fileId: mapping.fileId,
        payload: requestMappingPayload,
        stateMapping,
      });

      return acc;
    }, []);

    if (preparedMappings.length === 0) {
      toast({
        title: 'Nothing to save',
        description: 'Select at least one valid mapping before saving.',
        status: 'info',
        duration: 3500,
        isClosable: true,
      });
      return;
    }

    const payload = preparedMappings.map(({ fileId, payload }) => ({
      file_id: fileId,
      request_mapping: payload,
    }));

    try {
      await updateFileMappings(releaseId, payload);
      preparedMappings.forEach(({ fileId, stateMapping }) =>
        onMappingUpdate?.(fileId, stateMapping),
      );
    } catch (err) {
      console.error('Failed to update mappings:', err);
    }
  };

  const handleBulkRequestUpdate = (requestId: string) => {
    const request = requests.find((r) => r.id === requestId);
    if (!request) return;
    const seriesRequest = request.type === 'series' ? (request as SeriesRequest) : null;

    setMappings((prev) =>
      prev.map((mapping) => ({
        ...mapping,
        requestId,
        requestTitle: request.title,
        mappingType: request.type === 'series' ? 'series' : 'movie',
        season:
          request.type === 'series'
            ? (mapping.season ?? seriesRequest?.season_number ?? 1)
            : undefined,
        episode: request.type === 'series' ? (mapping.episode ?? 1) : undefined,
      })),
    );
  };

  const handleClearMapping = (fileId: string) => {
    setMappings((prev) =>
      prev.map((mapping) =>
        mapping.fileId === fileId
          ? {
              ...mapping,
              requestId: '',
              requestTitle: '',
              mappingType: 'movie',
              season: undefined,
              episode: undefined,
            }
          : mapping,
      ),
    );
  };

  const getFileMapping = (fileId: string) => mappings.find((m) => m.fileId === fileId);

  const getExistingMapping = (fileId: string) =>
    files.find((f) => f.id === fileId)?.request_mapping;

  const hasChanges = (fileId: string) => {
    const current = getFileMapping(fileId);
    const existing = getExistingMapping(fileId);
    const existingType: FileMapping['mappingType'] = existing
      ? existing.mapping_type === 'series'
        ? 'series'
        : 'movie'
      : 'movie';
    const existingSeason =
      existing && existing.mapping_type === 'series' ? existing.season : undefined;
    const existingEpisode =
      existing && existing.mapping_type === 'series' ? existing.episode : undefined;

    if (!current) return false;
    if (!existing && !current.requestId) return false;
    if (!existing && current.requestId) return true;

    return (
      current.requestId !== (existing?.request_id || '') ||
      current.requestTitle !== (existing?.request_title || '') ||
      current.mappingType !== existingType ||
      current.season !== existingSeason ||
      current.episode !== existingEpisode
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

          <Flex
            align={{ base: 'flex-start', md: 'center' }}
            direction={{ base: 'column', md: 'row' }}
            gap={3}
            wrap="wrap"
          >
            <Text fontWeight="600" fontSize="sm">
              Bulk assign to request:
            </Text>
            <Select
              placeholder={requestPlaceholder}
              value={selectedRequest}
              onChange={(e) => {
                setSelectedRequest(e.target.value);
                if (e.target.value) {
                  handleBulkRequestUpdate(e.target.value);
                }
              }}
              maxW="320px"
              size="sm"
              isDisabled={disableRequestSelection}
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

      {showRequestsLoading && (
        <Alert status="info" variant="subtle" borderRadius="md" alignItems="center" gap={3}>
          <Spinner size="sm" color="blue.400" />
          <AlertDescription fontSize="sm">Loading available requests...</AlertDescription>
        </Alert>
      )}

      {requestsErrorMessage && (
        <Alert
          status="error"
          borderRadius="md"
          alignItems="flex-start"
          flexDirection="column"
          gap={2}
        >
          <Flex align="center" gap={2} w="full">
            <AlertIcon />
            <AlertDescription fontSize="sm">{requestsErrorMessage}</AlertDescription>
          </Flex>
          <Button size="xs" onClick={() => refetchRequests()}>
            Retry loading requests
          </Button>
        </Alert>
      )}

      {!showRequestsLoading && !requestsErrorMessage && availableRequests.length === 0 && (
        <Alert status="warning" variant="subtle" borderRadius="md">
          <AlertIcon />
          <AlertDescription fontSize="sm">
            No requests are available yet. Mapping options will appear once requests finish loading.
          </AlertDescription>
        </Alert>
      )}

      {mappingError && (
        <Alert status="error" borderRadius="md" alignItems="flex-start">
          <AlertIcon />
          <AlertDescription fontSize="sm">{mappingError}</AlertDescription>
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
              No {showOnlyVideo ? 'video ' : ''}files available for mapping.
            </Text>
          </VStack>
        ) : (
          displayFiles.map((file) => {
            const mapping = getFileMapping(file.id);
            const existing = getExistingMapping(file.id);
            const changed = hasChanges(file.id);
            const existingType: FileMapping['mappingType'] = existing
              ? existing.mapping_type === 'series'
                ? 'series'
                : 'movie'
              : 'movie';
            const existingTypeLabel = existingType === 'series' ? 'Series' : 'Movie';
            const existingSeason =
              existing && existing.mapping_type === 'series' ? existing.season : undefined;
            const existingEpisode =
              existing && existing.mapping_type === 'series' ? existing.episode : undefined;

            return (
              <Box
                key={file.id}
                borderWidth="1px"
                borderRadius="lg"
                borderColor={existing ? 'blue.400' : 'border.muted'}
                bg={existing ? 'rgba(59, 130, 246, 0.14)' : 'bg.subtle'}
                p={4}
              >
                <Stack spacing={3}>
                  <Flex align="center" gap={3} wrap="wrap">
                    <Text fontSize="lg">{isVideoFile(file.name) ? '🎬' : '📄'}</Text>
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
                      Current: {existing.request_title} ({existingTypeLabel})
                      {existingSeason !== undefined &&
                        existingEpisode !== undefined &&
                        ` - S${existingSeason.toString().padStart(2, '0')}E${existingEpisode
                          .toString()
                          .padStart(2, '0')}`}
                    </Text>
                  )}

                  {!readonly && mapping && (
                    <Stack spacing={3}>
                      <Grid
                        templateColumns={{
                          base: 'repeat(1, minmax(0, 1fr))',
                          md: 'repeat(2, minmax(0, 1fr))',
                        }}
                        gap={3}
                      >
                        <Box>
                          <Text
                            fontSize="xs"
                            fontWeight="600"
                            textTransform="uppercase"
                            color="text.subtle"
                          >
                            Request
                          </Text>
                          <Select
                            placeholder={requestPlaceholder}
                            value={mapping.requestId}
                            size="sm"
                            isDisabled={disableRequestSelection}
                            onChange={(e) =>
                              handleMappingChange(file.id, 'requestId', e.target.value)
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
                          <Text
                            fontSize="xs"
                            fontWeight="600"
                            textTransform="uppercase"
                            color="text.subtle"
                          >
                            Mapping Type
                          </Text>
                          <Select
                            value={mapping.mappingType}
                            size="sm"
                            onChange={(e) =>
                              handleMappingChange(
                                file.id,
                                'mappingType',
                                e.target.value as FileMapping['mappingType'],
                              )
                            }
                          >
                            <option value="movie">Movie</option>
                            <option value="series">Series</option>
                          </Select>
                        </Box>
                      </Grid>

                      {mapping.mappingType === 'series' && (
                        <Grid templateColumns="repeat(2, minmax(0, 1fr))" gap={3}>
                          <Box>
                            <Text
                              fontSize="xs"
                              fontWeight="600"
                              textTransform="uppercase"
                              color="text.subtle"
                            >
                              Season
                            </Text>
                            <Input
                              type="number"
                              min={1}
                              max={99}
                              value={mapping.season ?? ''}
                              placeholder="e.g. 2"
                              size="sm"
                              isRequired
                              onChange={(e) =>
                                handleMappingChange(
                                  file.id,
                                  'season',
                                  e.target.value ? parseInt(e.target.value, 10) : undefined,
                                )
                              }
                            />
                          </Box>
                          <Box>
                            <Text
                              fontSize="xs"
                              fontWeight="600"
                              textTransform="uppercase"
                              color="text.subtle"
                            >
                              Episode
                            </Text>
                            <Input
                              type="number"
                              min={1}
                              max={999}
                              value={mapping.episode ?? ''}
                              placeholder="e.g. 5"
                              size="sm"
                              isRequired
                              onChange={(e) =>
                                handleMappingChange(
                                  file.id,
                                  'episode',
                                  e.target.value ? parseInt(e.target.value, 10) : undefined,
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
                      {existing.request_title} ({existingTypeLabel})
                      {existingSeason !== undefined &&
                        existingEpisode !== undefined &&
                        ` - S${existingSeason.toString().padStart(2, '0')}E${existingEpisode
                          .toString()
                          .padStart(2, '0')}`}
                    </Text>
                  )}

                  {!readonly && (
                    <Flex gap={2} justify="flex-end" flexWrap="wrap">
                      <Button
                        size="sm"
                        colorScheme="blue"
                        variant={changed && mapping?.requestId ? 'solid' : 'outline'}
                        onClick={() => handleSaveMapping(file.id)}
                        isDisabled={isSaving || !changed || !mapping?.requestId || requestsLoading}
                      >
                        {isSaving ? 'Saving...' : 'Save'}
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
          direction={{ base: 'column', md: 'row' }}
          justify="space-between"
          align={{ base: 'flex-start', md: 'center' }}
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
            variant={mappings.some((m) => hasChanges(m.fileId)) ? 'solid' : 'outline'}
            isDisabled={isSaving || !mappings.some((m) => hasChanges(m.fileId)) || requestsLoading}
          >
            {isSaving ? 'Saving All...' : 'Save All Changes'}
          </Button>
        </Flex>
      )}

      {!showOnlyVideo && (
        <Text fontSize="sm" color="text.subtle">
          File types: {video.length} video, {subtitle.length} subtitle, {other.length} other
        </Text>
      )}

      <Text fontSize="sm" color="text.subtle">
        Available requests: {movieRequests.length} movies, {seriesRequests.length} series
      </Text>
    </Stack>
  );
};

export default FileRequestMapping;
