import { CloseIcon, RepeatIcon } from '@chakra-ui/icons';
import {
  Alert,
  AlertDescription,
  AlertIcon,
  Box,
  Button,
  Checkbox,
  Flex,
  FormControl,
  FormLabel,
  Grid,
  Heading,
  IconButton,
  Input,
  InputGroup,
  InputRightElement,
  NumberInput,
  NumberInputField,
  Select,
  Spinner,
  Stack,
  Tag,
  Text,
  VStack,
  useOutsideClick,
  useToast,
} from '@chakra-ui/react';
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Controller, useFieldArray, useForm, type SubmitHandler } from 'react-hook-form';

import { useReleaseFileMapping } from '@/hooks/useReleases';
import { useRequestsList } from '@/hooks/useRequests';
import type {
  FileRequestMapping as FileRequestMappingType,
  MediaRequest,
  ReleaseFile,
  ReleaseFileMappingInput,
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

type MappingType = 'movie' | 'series';

interface MappingFormValue {
  fileId: string;
  requestId: string;
  requestTitle: string;
  mappingType: MappingType;
  season?: number;
  episode?: number;
}

interface FileMappingFormValues {
  mappings: MappingFormValue[];
  showOnlyVideo: boolean;
}

interface RequestOption {
  value: string;
  label: string;
  request: MediaRequest;
}

type ParsedEpisodeMetadata = {
  season?: number;
  episode?: number;
};

const buildMappingDefaults = (
  files: ReleaseFile[],
  defaultRequest: FileRequestMappingProps['defaultRequest'],
  parsedMetadata: Map<string, ParsedEpisodeMetadata>,
): MappingFormValue[] => {
  return files.map((file) => {
    const existing = file.request_mapping;
    const inferred = parsedMetadata.get(file.id) ?? {};

    if (existing?.mapping_type === 'series') {
      return {
        fileId: file.id,
        requestId: existing.request_id,
        requestTitle: existing.request_title ?? '',
        mappingType: 'series',
        season: existing.season ?? inferred.season ?? 1,
        episode: existing.episode ?? inferred.episode ?? 1,
      } satisfies MappingFormValue;
    }

    if (existing?.mapping_type === 'movie') {
      return {
        fileId: file.id,
        requestId: existing.request_id,
        requestTitle: existing.request_title ?? '',
        mappingType: 'movie',
      } satisfies MappingFormValue;
    }

    const fallbackType: MappingType = defaultRequest?.type === 'series' ? 'series' : 'movie';
    const fallbackSeason =
      fallbackType === 'series'
        ? defaultRequest?.season_number ?? inferred.season ?? 1
        : undefined;
    const fallbackEpisode =
      fallbackType === 'series' ? inferred.episode ?? 1 : undefined;

    return fallbackType === 'series'
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
  });
};

const createDefaultValues = (
  files: ReleaseFile[],
  defaultRequest: FileRequestMappingProps['defaultRequest'],
  parsedMetadata: Map<string, ParsedEpisodeMetadata>,
): FileMappingFormValues => ({
  mappings: buildMappingDefaults(files, defaultRequest, parsedMetadata),
  showOnlyVideo: true,
});

const RequestCombobox: React.FC<{
  value: string;
  options: RequestOption[];
  placeholder: string;
  onSelect: (option: RequestOption | null) => void;
  isDisabled?: boolean;
}> = ({ value, options, placeholder, onSelect, isDisabled = false }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');

  const selectedOption = useMemo(
    () => options.find((option) => option.value === value) ?? null,
    [options, value],
  );

  useEffect(() => {
    setQuery(selectedOption?.label ?? '');
  }, [selectedOption?.label]);

  useOutsideClick({
    ref: containerRef,
    handler: () => setIsOpen(false),
  });

  const filteredOptions = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) {
      return options;
    }
    return options.filter((option) => option.label.toLowerCase().includes(normalized));
  }, [options, query]);

  const handleSelect = (option: RequestOption | null) => {
    onSelect(option);
    setIsOpen(false);
    setQuery(option?.label ?? '');
  };

  return (
    <Box ref={containerRef} position="relative">
      <InputGroup size="sm">
        <Input
          value={query}
          placeholder={placeholder}
          onFocus={() => !isDisabled && setIsOpen(true)}
          onChange={(event) => {
            setQuery(event.target.value);
            if (!isOpen) {
              setIsOpen(true);
            }
          }}
          isDisabled={isDisabled}
          autoComplete="off"
          role="combobox"
          aria-expanded={isOpen}
        />
        {selectedOption && !isDisabled && (
          <InputRightElement h="100%" pe={1}>
            <IconButton
              size="xs"
              variant="ghost"
              aria-label="Clear selection"
              icon={<CloseIcon boxSize={2.5} />}
              onClick={() => handleSelect(null)}
            />
          </InputRightElement>
        )}
      </InputGroup>
      {isOpen && !isDisabled && (
        <Box
          position="absolute"
          zIndex="popover"
          left={0}
          right={0}
          mt={1}
          maxH="240px"
          overflowY="auto"
          borderWidth="1px"
          borderRadius="md"
          bg="bg.surface"
          borderColor="border.muted"
          shadow="lg"
        >
          <Stack spacing={0}>
            {filteredOptions.length === 0 && (
              <Text px={3} py={2} fontSize="sm" color="text.subtle">
                No matching requests
              </Text>
            )}
            {filteredOptions.map((option) => (
              <Button
                key={option.value}
                variant="ghost"
                justifyContent="flex-start"
                fontWeight="normal"
                fontSize="sm"
                borderRadius={0}
                onMouseDown={(event) => {
                  event.preventDefault();
                  handleSelect(option);
                }}
                bg={option.value === value ? 'rgba(59, 130, 246, 0.16)' : 'transparent'}
              >
                {option.label}
              </Button>
            ))}
          </Stack>
        </Box>
      )}
    </Box>
  );
};

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
  const toast = useToast();

  const parsedFileMetadata = useMemo(() => {
    const metadata = new Map<string, ParsedEpisodeMetadata>();
    files.forEach((file) => {
      const parsed = parseSeriesEpisodeFromFilename(file.name);
      metadata.set(file.id, parsed ?? {});
    });
    return metadata;
  }, [files]);

  const form = useForm<FileMappingFormValues>({
    defaultValues: createDefaultValues(files, defaultRequest, parsedFileMetadata),
    mode: 'onChange',
  });

  const { control, handleSubmit, reset, watch, setValue, getValues } = form;

  const { fields } = useFieldArray({ control, name: 'mappings' });

  const showOnlyVideo = watch('showOnlyVideo');
  const mappingValues = (watch('mappings') as MappingFormValue[]) ?? [];

  const groupedFiles = useMemo(() => groupFilesByType(files), [files]);
  const { video } = groupedFiles;
  const displayFiles = useMemo(
    () => (showOnlyVideo ? video : files),
    [showOnlyVideo, video, files],
  );

  useEffect(() => {
    const currentShowOnlyVideo = getValues('showOnlyVideo');
    const existingMappings = getValues('mappings');
    const currentById = new Map<string, MappingFormValue>(
      (existingMappings ?? []).map((entry) => [entry.fileId, entry] as const),
    );
    const defaults = buildMappingDefaults(files, defaultRequest, parsedFileMetadata);
    const merged = defaults.map((item) => currentById.get(item.fileId) ?? item);

    reset({ mappings: merged, showOnlyVideo: currentShowOnlyVideo ?? true });
  }, [files, defaultRequest, parsedFileMetadata, getValues, reset]);

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

  const requestOptions = useMemo<RequestOption[]>(
    () =>
      availableRequests.map((request) => ({
        value: request.id,
        label: `${request.title} (${request.year})`,
        request,
      })),
    [availableRequests],
  );

  const requestsById = useMemo(() => {
    const map = new Map<string, MediaRequest>();
    availableRequests.forEach((request) => {
      map.set(request.id, request);
    });
    return map;
  }, [availableRequests]);

  const defaultSeriesSeason = useMemo(
    () => (defaultRequest?.type === 'series' ? defaultRequest?.season_number ?? 1 : 1),
    [defaultRequest],
  );

  const requestsErrorMessage =
    requestsError instanceof Error
      ? requestsError.message
      : requestsError
        ? 'Failed to load requests'
        : null;

  const showRequestsLoading = (requestsLoading || isRequestsFetching) && requests.length === 0;

  const disableRequestSelection =
    readonly || showRequestsLoading || Boolean(requestsErrorMessage) || availableRequests.length === 0;

  const requestPlaceholder = showRequestsLoading
    ? 'Loading requests...'
    : requestsErrorMessage
      ? 'Unable to load requests'
      : 'Select a request...';

  const fileIndexMap = useMemo(() => {
    const indexMap = new Map<string, number>();
    fields.forEach((field, index) => {
      indexMap.set(field.fileId, index);
    });
    return indexMap;
  }, [fields]);

  const getMappingValue = useCallback(
    (fileId: string) => {
      const index = fileIndexMap.get(fileId);
      if (index === undefined) {
        return undefined;
      }
      return mappingValues[index];
    },
    [fileIndexMap, mappingValues],
  );

  const setMappingValue = useCallback(
    (fileId: string, key: keyof MappingFormValue, value: unknown) => {
      const index = fileIndexMap.get(fileId);
      if (index === undefined) {
        return;
      }
      setValue(`mappings.${index}.${key}`, value as MappingFormValue[keyof MappingFormValue], {
        shouldDirty: true,
        shouldTouch: true,
      });
    },
    [fileIndexMap, setValue],
  );

  const handleRequestSelect = useCallback(
    (fileId: string, option: RequestOption | null) => {
      if (!option) {
        setMappingValue(fileId, 'requestId', '');
        setMappingValue(fileId, 'requestTitle', '');
        setMappingValue(fileId, 'mappingType', 'movie');
        setMappingValue(fileId, 'season', undefined);
        setMappingValue(fileId, 'episode', undefined);
        return;
      }

      const request = option.request;
      const mappingType: MappingType = request.type === 'series' ? 'series' : 'movie';
      const parsed = parsedFileMetadata.get(fileId) ?? {};

      setMappingValue(fileId, 'requestId', request.id);
      setMappingValue(fileId, 'requestTitle', request.title);
      setMappingValue(fileId, 'mappingType', mappingType);

      if (mappingType === 'series') {
        const current = getMappingValue(fileId);
        const requestSeason = (request as SeriesRequest).season_number ?? 1;
        const currentSeason = current?.season ?? parsed.season ?? requestSeason;
        const currentEpisode = current?.episode ?? parsed.episode ?? 1;
        setMappingValue(fileId, 'season', currentSeason);
        setMappingValue(fileId, 'episode', currentEpisode);
      } else {
        setMappingValue(fileId, 'season', undefined);
        setMappingValue(fileId, 'episode', undefined);
      }
    },
    [getMappingValue, parsedFileMetadata, setMappingValue],
  );

  const handleBulkRequestUpdate = useCallback(
    (requestId: string) => {
      const request = availableRequests.find((candidate) => candidate.id === requestId);
      if (!request) {
        return;
      }
      const mappingType: MappingType = request.type === 'series' ? 'series' : 'movie';
      const seasonNumber = request.type === 'series' ? (request as SeriesRequest).season_number ?? 1 : undefined;

      mappingValues.forEach((mapping) => {
        setMappingValue(mapping.fileId, 'requestId', request.id);
        setMappingValue(mapping.fileId, 'requestTitle', request.title);
        setMappingValue(mapping.fileId, 'mappingType', mappingType);
        if (mappingType === 'series') {
          const parsed = parsedFileMetadata.get(mapping.fileId) ?? {};
          const currentSeason =
            parsed.season ?? mapping.season ?? seasonNumber ?? 1;
          const currentEpisode = parsed.episode ?? mapping.episode ?? 1;
          setMappingValue(mapping.fileId, 'season', currentSeason);
          setMappingValue(mapping.fileId, 'episode', currentEpisode);
        } else {
          setMappingValue(mapping.fileId, 'season', undefined);
          setMappingValue(mapping.fileId, 'episode', undefined);
        }
      });
    },
    [availableRequests, mappingValues, parsedFileMetadata, setMappingValue],
  );

  const handleClearMapping = useCallback(
    (fileId: string) => {
      setMappingValue(fileId, 'requestId', '');
      setMappingValue(fileId, 'requestTitle', '');
      setMappingValue(fileId, 'mappingType', 'movie');
      setMappingValue(fileId, 'season', undefined);
      setMappingValue(fileId, 'episode', undefined);
    },
    [setMappingValue],
  );

  const hasChanges = useCallback(
    (fileId: string) => {
      const current = getMappingValue(fileId);
      const existing = files.find((file) => file.id === fileId)?.request_mapping;
      if (!current) return false;
      if (!existing) {
        return Boolean(current.requestId);
      }

      const existingType: MappingType = existing.mapping_type === 'series' ? 'series' : 'movie';
      const existingSeason =
        existingType === 'series' && existing.mapping_type === 'series'
          ? existing.season
          : undefined;
      const existingEpisode =
        existingType === 'series' && existing.mapping_type === 'series'
          ? existing.episode
          : undefined;

      return (
        current.requestId !== existing.request_id ||
        current.requestTitle !== (existing.request_title ?? '') ||
        current.mappingType !== existingType ||
        current.season !== existingSeason ||
        current.episode !== existingEpisode
      );
    },
    [files, getMappingValue],
  );

  const prepareMappingPayload = useCallback((mapping: MappingFormValue) => {
    if (!mapping.requestId) {
      return null;
    }

    if (mapping.mappingType === 'series') {
      return {
        payload: {
          request_id: mapping.requestId,
          mapping_type: 'series' as const,
          season: mapping.season ?? 1,
          episode: mapping.episode ?? 1,
        },
        stateMapping: {
          request_id: mapping.requestId,
          mapping_type: 'series' as const,
          season: mapping.season ?? 1,
          episode: mapping.episode ?? 1,
          request_title: mapping.requestTitle,
        },
      };
    }

    return {
      payload: {
        request_id: mapping.requestId,
        mapping_type: 'movie' as const,
      },
      stateMapping: {
        request_id: mapping.requestId,
        mapping_type: 'movie' as const,
        request_title: mapping.requestTitle,
      },
    };
  }, []);

  type PreparedMapping = {
    fileId: string;
    payload: ReleaseFileMappingInput;
    stateMapping: FileRequestMappingType;
  };

  const persistMappings = useCallback(
    async (
      entries: Array<{ fileId: string; mapping: MappingFormValue }>,
      onSuccess?: () => void,
    ) => {
      const prepared = entries
        .map(({ fileId, mapping }): PreparedMapping | null => {
          const outcome = prepareMappingPayload(mapping);
          if (!outcome) {
            return null;
          }
          if (!validateRequestMapping(outcome.payload)) {
            return null;
          }
          const apiPayload: ReleaseFileMappingInput = {
            file_id: fileId,
            request_mapping: outcome.payload,
          };
          return {
            fileId,
            payload: apiPayload,
            stateMapping: outcome.stateMapping,
          };
        })
        .filter((entry): entry is PreparedMapping => Boolean(entry));

      if (prepared.length === 0) {
        toast({
          title: 'Nothing to save',
          description: 'Select at least one valid mapping before saving.',
          status: 'info',
          duration: 3500,
          isClosable: true,
        });
        return;
      }

      try {
        await updateFileMappings(
          releaseId,
          prepared.map((item) => item.payload),
        );
        prepared.forEach((item) => onMappingUpdate?.(item.fileId, item.stateMapping));
        onSuccess?.();
      } catch (error) {
        console.error('Failed to update mappings:', error);
        toast({
          title: 'Failed to update mappings',
          description: error instanceof Error ? error.message : undefined,
          status: 'error',
          duration: 4000,
          isClosable: true,
        });
      }
    },
    [onMappingUpdate, prepareMappingPayload, releaseId, toast, updateFileMappings],
  );

  const handleAutoFillEpisodes = useCallback(() => {
    const applicableEntries = files
      .map((file) => ({ file, mapping: getMappingValue(file.id) }))
      .filter(
        (entry): entry is { file: ReleaseFile; mapping: MappingFormValue } =>
          Boolean(entry.mapping?.requestId) && entry.mapping?.mappingType === 'series',
      );

    if (applicableEntries.length === 0) {
      toast({
        title: 'No series mappings to update',
        description: 'Assign a series request before auto-filling episodes.',
        status: 'info',
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    const sortedEntries = applicableEntries.sort((a, b) =>
      a.file.name.localeCompare(b.file.name),
    );

    let sequentialEpisode = 1;

    sortedEntries.forEach(({ file, mapping }) => {
      const parsed = parsedFileMetadata.get(file.id) ?? {};
      const matchedRequest = mapping.requestId ? requestsById.get(mapping.requestId) : undefined;
      const requestSeasonDefault =
        matchedRequest && matchedRequest.type === 'series'
          ? (matchedRequest as SeriesRequest).season_number ?? defaultSeriesSeason
          : defaultSeriesSeason;

      const season = parsed.season ?? mapping.season ?? requestSeasonDefault ?? defaultSeriesSeason;

      let episode: number;
      if (parsed.episode) {
        episode = parsed.episode;
        sequentialEpisode = Math.max(sequentialEpisode, parsed.episode + 1);
      } else if (mapping.episode) {
        episode = mapping.episode;
        sequentialEpisode = Math.max(sequentialEpisode, mapping.episode + 1);
      } else {
        episode = sequentialEpisode;
        sequentialEpisode += 1;
      }

      setMappingValue(file.id, 'season', season);
      setMappingValue(file.id, 'episode', episode);
    });

    toast({
      title: 'Episodes auto-filled',
      description: 'Season and episode numbers were inferred from the filenames.',
      status: 'success',
      duration: 3000,
      isClosable: true,
    });
  }, [
    defaultSeriesSeason,
    files,
    getMappingValue,
    parsedFileMetadata,
    requestsById,
    setMappingValue,
    toast,
  ]);

  const canAutoFillEpisodes = useMemo(
    () =>
      mappingValues.some(
        (mapping) => mapping.mappingType === 'series' && Boolean(mapping.requestId),
      ),
    [mappingValues],
  );

  const handleSaveSingle = useCallback(
    async (fileId: string) => {
      const mapping = getMappingValue(fileId);
      if (!mapping) {
        return;
      }
      await persistMappings([{ fileId, mapping }]);
    },
    [getMappingValue, persistMappings],
  );

  const resetToDefaults = useCallback(() => {
    const keepVideoOnly = getValues('showOnlyVideo');
    reset({
      mappings: buildMappingDefaults(files, defaultRequest, parsedFileMetadata),
      showOnlyVideo: keepVideoOnly ?? true,
    });
  }, [defaultRequest, files, getValues, parsedFileMetadata, reset]);

  const onSubmitAll: SubmitHandler<FileMappingFormValues> = async (values) => {
    await persistMappings(
      values.mappings.map((mapping) => ({ fileId: mapping.fileId, mapping })),
      () => {
        reset({ ...values });
      },
    );
  };

  return (
    <Stack spacing={6} as="form" onSubmit={handleSubmit(onSubmitAll)}>
      <Stack spacing={1}>
        <Heading size="md">🔗 File Request Mapping</Heading>
        <Text fontSize="sm" color="text.subtle">
          Map release files to other requests to manage shared content.
        </Text>
      </Stack>

      {!readonly && (
        <Stack spacing={4}>
          <Flex gap={4} wrap="wrap" align="center">
            <Controller
              name="showOnlyVideo"
              control={control}
              render={({ field }) => (
                <Checkbox
                  colorScheme="blue"
                  isChecked={field.value}
                  onChange={(event) => field.onChange(event.target.checked)}
                >
                  Show only video files ({video.length})
                </Checkbox>
              )}
            />
            <Button
              size="sm"
              variant="outline"
              leftIcon={<RepeatIcon />}
              onClick={() => resetToDefaults()}
            >
              Reset changes
            </Button>
          </Flex>

          <Flex
            align={{ base: 'flex-start', md: 'center' }}
            direction={{ base: 'column', md: 'row' }}
            gap={3}
            wrap="wrap"
          >
            <FormControl maxW="320px" isDisabled={disableRequestSelection}>
              <FormLabel fontSize="sm" fontWeight="600">
                Apply request to all files
              </FormLabel>
              <Select
                placeholder={requestPlaceholder}
                size="sm"
                onChange={(event) => handleBulkRequestUpdate(event.target.value)}
                value=""
              >
                <option value="" disabled hidden>
                  {requestPlaceholder}
                </option>
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
            </FormControl>
            <Button
              size="sm"
              variant="outline"
              onClick={handleAutoFillEpisodes}
              isDisabled={!canAutoFillEpisodes}
            >
              Auto-fill from filenames
            </Button>
            <Button
              size="sm"
              onClick={() => refetchRequests()}
              leftIcon={isRequestsFetching ? <Spinner size="sm" /> : undefined}
            >
              Refresh requests
            </Button>
          </Flex>
        </Stack>
      )}

      {requestsErrorMessage && (
        <Alert status="error" borderRadius="md">
          <AlertIcon />
          <AlertDescription fontSize="sm">{requestsErrorMessage}</AlertDescription>
        </Alert>
      )}

      {availableRequests.length === 0 && !showRequestsLoading && !requestsErrorMessage && (
        <Alert status="info" borderRadius="md">
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
            const mappingIndex = fileIndexMap.get(file.id);
            if (mappingIndex === undefined) {
              return null;
            }

            const mapping = mappingValues?.[mappingIndex];
            const existing = files.find((candidate) => candidate.id === file.id)?.request_mapping;
            const changed = hasChanges(file.id);
            const existingType: MappingType = existing
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
                        <FormControl>
                          <FormLabel fontSize="xs" fontWeight="600" textTransform="uppercase" color="text.subtle">
                            Request
                          </FormLabel>
                          <Controller
                            control={control}
                            name={`mappings.${mappingIndex}.requestId`}
                            render={({ field }) => (
                              <RequestCombobox
                                value={field.value}
                                options={requestOptions}
                                placeholder={requestPlaceholder}
                                onSelect={(option) => {
                                  field.onChange(option?.value ?? '');
                                  handleRequestSelect(file.id, option);
                                }}
                                isDisabled={disableRequestSelection}
                              />
                            )}
                          />
                        </FormControl>

                        <FormControl>
                          <FormLabel fontSize="xs" fontWeight="600" textTransform="uppercase" color="text.subtle">
                            Mapping Type
                          </FormLabel>
                          <Controller
                            control={control}
                            name={`mappings.${mappingIndex}.mappingType`}
                            render={({ field }) => (
                              <Select
                                size="sm"
                                value={field.value}
                                onChange={(event) => {
                                  const nextType = event.target.value as MappingType;
                                  field.onChange(nextType);
                                  if (nextType === 'movie') {
                                    setMappingValue(file.id, 'season', undefined);
                                    setMappingValue(file.id, 'episode', undefined);
                                  } else {
                                    const current = getMappingValue(file.id);
                                    setMappingValue(file.id, 'season', current?.season ?? 1);
                                    setMappingValue(file.id, 'episode', current?.episode ?? 1);
                                  }
                                }}
                                isDisabled={!mapping.requestId}
                              >
                                <option value="movie">Movie</option>
                                <option value="series">Series</option>
                              </Select>
                            )}
                          />
                        </FormControl>

                        {mapping.mappingType === 'series' && (
                          <FormControl>
                            <FormLabel fontSize="xs" fontWeight="600" textTransform="uppercase" color="text.subtle">
                              Season
                            </FormLabel>
                            <Controller
                              control={control}
                              name={`mappings.${mappingIndex}.season`}
                              render={({ field }) => (
                                <NumberInput
                                  size="sm"
                                  min={1}
                                  value={field.value ?? ''}
                                  onChange={(_, valueNumber) =>
                                    field.onChange(Number.isNaN(valueNumber) ? undefined : valueNumber)
                                  }
                                  isDisabled={mapping.mappingType !== 'series'}
                                >
                                  <NumberInputField />
                                </NumberInput>
                              )}
                            />
                          </FormControl>
                        )}

                        {mapping.mappingType === 'series' && (
                          <FormControl>
                            <FormLabel fontSize="xs" fontWeight="600" textTransform="uppercase" color="text.subtle">
                              Episode
                            </FormLabel>
                            <Controller
                              control={control}
                              name={`mappings.${mappingIndex}.episode`}
                              render={({ field }) => (
                                <NumberInput
                                  size="sm"
                                  min={1}
                                  value={field.value ?? ''}
                                  onChange={(_, valueNumber) =>
                                    field.onChange(Number.isNaN(valueNumber) ? undefined : valueNumber)
                                  }
                                  isDisabled={mapping.mappingType !== 'series'}
                                >
                                  <NumberInputField />
                                </NumberInput>
                              )}
                            />
                          </FormControl>
                        )}
                      </Grid>

                      <Flex gap={2} wrap="wrap">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleClearMapping(file.id)}
                          isDisabled={!mapping.requestId}
                        >
                          Clear
                        </Button>
                        <Button
                          size="sm"
                          colorScheme="blue"
                          onClick={() => handleSaveSingle(file.id)}
                          isLoading={isSaving}
                          isDisabled={!mapping.requestId || isSaving}
                        >
                          Save mapping
                        </Button>
                      </Flex>
                    </Stack>
                  )}

                  {readonly && existing && (
                    <Text fontSize="sm" color="text.subtle">
                      This release is already mapped. Editing is disabled in read-only mode.
                    </Text>
                  )}
                </Stack>
              </Box>
            );
          })
        )}
      </Stack>

      {!readonly && (
        <Flex justify="flex-end" gap={3} wrap="wrap">
          <Button variant="outline" onClick={() => resetToDefaults()}>
            Undo all changes
          </Button>
          <Button type="submit" colorScheme="blue" isLoading={isSaving}>
            Save all mappings
          </Button>
        </Flex>
      )}
    </Stack>
  );
};

export default FileRequestMapping;
