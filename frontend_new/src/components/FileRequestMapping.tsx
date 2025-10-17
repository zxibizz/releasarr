import React, { useEffect, useState } from "react";
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
  onClose,
  readonly = false,
}) => {
  const { updateFileMapping, loading, error } = useReleaseFileMapping();
  const { requests } = useRequests();
  const [mappings, setMappings] = useState<FileMapping[]>([]);
  const [showOnlyVideo, setShowOnlyVideo] = useState(true);
  const [selectedRequest, setSelectedRequest] = useState<string>("");

  const { video, subtitle, other } = groupFilesByType(files);
  const displayFiles = showOnlyVideo ? video : files;

  useEffect(() => {
    // Initialize mappings from existing data
    const initialMappings = displayFiles.map((file) => {
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
  }, [displayFiles]);

  const handleMappingChange = (
    fileId: string,
    field: keyof Omit<FileMapping, "fileId">,
    value: string | number | undefined
  ) => {
    setMappings((prev) =>
      prev.map((mapping) => {
        if (mapping.fileId === fileId) {
          const updated = { ...mapping, [field]: value };

          // Auto-update request title when request ID changes
          if (field === "requestId") {
            const request = requests.find((r) => r.id === value);
            updated.requestTitle = request?.title || "";

            // Auto-suggest mapping type based on request type
            if (request) {
              updated.mappingType =
                request.type === "series" ? "episode" : "movie";
            }
          }

          return updated;
        }
        return mapping;
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
    } catch (error) {
      console.error("Failed to update mapping:", error);
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
        } catch (error) {
          console.error(
            `Failed to update mapping for ${mapping.fileId}:`,
            error
          );
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

  const getFileMapping = (fileId: string) => {
    return mappings.find((m) => m.fileId === fileId);
  };

  const getExistingMapping = (fileId: string) => {
    const file = files.find((f) => f.id === fileId);
    return file?.request_mapping;
  };

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

  const getAvailableRequests = () => {
    return requests.filter((request) => request.status !== "failed");
  };

  const groupRequestsByType = () => {
    const availableRequests = getAvailableRequests();
    return {
      movies: availableRequests.filter((r) => r.type === "movie"),
      series: availableRequests.filter((r) => r.type === "series"),
    };
  };

  const { movies, series } = groupRequestsByType();

  return (
    <div className="bg-white rounded-lg shadow-lg border border-gray-200">
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900">
            File Request Mapping
          </h3>
          {onClose && (
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
            >
              ✕
            </button>
          )}
        </div>
        <p className="text-sm text-gray-600 mt-1">
          Map release files to specific requests for cross-request collections.
        </p>
      </div>

      <div className="p-6">
        {/* Controls */}
        {!readonly && (
          <div className="mb-6 space-y-4">
            <div className="flex flex-wrap items-center gap-4">
              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="showOnlyVideo"
                  checked={showOnlyVideo}
                  onChange={(e) => setShowOnlyVideo(e.target.checked)}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <label
                  htmlFor="showOnlyVideo"
                  className="text-sm text-gray-700"
                >
                  Show only video files ({video.length})
                </label>
              </div>
            </div>

            <div className="flex items-center space-x-4">
              <label className="text-sm font-medium text-gray-700">
                Bulk assign to request:
              </label>
              <select
                value={selectedRequest}
                onChange={(e) => {
                  setSelectedRequest(e.target.value);
                  if (e.target.value) {
                    handleBulkRequestUpdate(e.target.value);
                  }
                }}
                className="border border-gray-300 rounded-md px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Select a request...</option>
                {movies.length > 0 && (
                  <optgroup label="Movies">
                    {movies.map((request) => (
                      <option key={request.id} value={request.id}>
                        {request.title} ({request.year})
                      </option>
                    ))}
                  </optgroup>
                )}
                {series.length > 0 && (
                  <optgroup label="Series">
                    {series.map((request) => (
                      <option key={request.id} value={request.id}>
                        {request.title} ({request.year})
                      </option>
                    ))}
                  </optgroup>
                )}
              </select>
            </div>
          </div>
        )}

        {/* Error Display */}
        {error && (
          <div className="mb-4 bg-red-50 border border-red-200 rounded-lg p-3">
            <div className="text-red-800 text-sm">{error}</div>
          </div>
        )}

        {/* Files List */}
        <div className="space-y-4">
          {displayFiles.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              No {showOnlyVideo ? "video " : ""}files to map.
            </div>
          ) : (
            displayFiles.map((file) => {
              const mapping = getFileMapping(file.id);
              const existing = getExistingMapping(file.id);
              const changed = hasChanges(file.id);

              return (
                <div
                  key={file.id}
                  className={`border rounded-lg p-4 ${
                    existing
                      ? "border-blue-200 bg-blue-50"
                      : "border-gray-200 bg-white"
                  }`}
                >
                  <div className="flex items-start space-x-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2 mb-2">
                        <span className="text-lg">
                          {isVideoFile(file.name) ? "🎬" : "📄"}
                        </span>
                        <h4 className="text-sm font-medium text-gray-900 truncate">
                          {file.name}
                        </h4>
                        <span className="text-xs text-gray-500">
                          ({formatFileSize(file.size)})
                        </span>
                        {existing && (
                          <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full">
                            Mapped
                          </span>
                        )}
                        {changed && (
                          <span className="px-2 py-1 bg-yellow-100 text-yellow-800 text-xs rounded-full">
                            Changed
                          </span>
                        )}
                      </div>

                      {existing && (
                        <div className="text-sm text-gray-600 mb-2">
                          Current: {existing.request_title} (
                          {existing.mapping_type})
                          {existing.season &&
                            existing.episode &&
                            ` - S${existing.season
                              .toString()
                              .padStart(2, "0")}E${existing.episode
                              .toString()
                              .padStart(2, "0")}`}
                        </div>
                      )}

                      {!readonly && mapping && (
                        <div className="space-y-3">
                          {/* Request Selection */}
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                            <div>
                              <label className="block text-xs font-medium text-gray-700 mb-1">
                                Request
                              </label>
                              <select
                                value={mapping.requestId}
                                onChange={(e) =>
                                  handleMappingChange(
                                    file.id,
                                    "requestId",
                                    e.target.value
                                  )
                                }
                                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                              >
                                <option value="">Select request...</option>
                                {movies.length > 0 && (
                                  <optgroup label="Movies">
                                    {movies.map((request) => (
                                      <option
                                        key={request.id}
                                        value={request.id}
                                      >
                                        {request.title} ({request.year})
                                      </option>
                                    ))}
                                  </optgroup>
                                )}
                                {series.length > 0 && (
                                  <optgroup label="Series">
                                    {series.map((request) => (
                                      <option
                                        key={request.id}
                                        value={request.id}
                                      >
                                        {request.title} ({request.year})
                                      </option>
                                    ))}
                                  </optgroup>
                                )}
                              </select>
                            </div>

                            <div>
                              <label className="block text-xs font-medium text-gray-700 mb-1">
                                Mapping Type
                              </label>
                              <select
                                value={mapping.mappingType}
                                onChange={(e) =>
                                  handleMappingChange(
                                    file.id,
                                    "mappingType",
                                    e.target.value as
                                      | "episode"
                                      | "movie"
                                      | "season"
                                  )
                                }
                                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                              >
                                <option value="movie">Movie</option>
                                <option value="episode">Episode</option>
                                <option value="season">Season</option>
                              </select>
                            </div>
                          </div>

                          {/* Episode Details (for series) */}
                          {mapping.mappingType === "episode" && (
                            <div className="grid grid-cols-2 gap-3">
                              <div>
                                <label className="block text-xs font-medium text-gray-700 mb-1">
                                  Season
                                </label>
                                <input
                                  type="number"
                                  min="1"
                                  max="99"
                                  value={mapping.season?.toString() || ""}
                                  onChange={(e) =>
                                    handleMappingChange(
                                      file.id,
                                      "season",
                                      e.target.value
                                        ? parseInt(e.target.value)
                                        : undefined
                                    )
                                  }
                                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                                />
                              </div>

                              <div>
                                <label className="block text-xs font-medium text-gray-700 mb-1">
                                  Episode
                                </label>
                                <input
                                  type="number"
                                  min="1"
                                  max="999"
                                  value={mapping.episode?.toString() || ""}
                                  onChange={(e) =>
                                    handleMappingChange(
                                      file.id,
                                      "episode",
                                      e.target.value
                                        ? parseInt(e.target.value)
                                        : undefined
                                    )
                                  }
                                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                                />
                              </div>
                            </div>
                          )}

                          {mapping.mappingType === "season" && (
                            <div className="grid grid-cols-1 gap-3">
                              <div>
                                <label className="block text-xs font-medium text-gray-700 mb-1">
                                  Season
                                </label>
                                <input
                                  type="number"
                                  min="1"
                                  max="99"
                                  value={mapping.season?.toString() || ""}
                                  onChange={(e) =>
                                    handleMappingChange(
                                      file.id,
                                      "season",
                                      e.target.value
                                        ? parseInt(e.target.value)
                                        : undefined
                                    )
                                  }
                                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                                />
                              </div>
                            </div>
                          )}
                        </div>
                      )}

                      {readonly && existing && (
                        <div className="text-sm text-gray-900">
                          {existing.request_title} ({existing.mapping_type})
                          {existing.season &&
                            existing.episode &&
                            ` - S${existing.season
                              .toString()
                              .padStart(2, "0")}E${existing.episode
                              .toString()
                              .padStart(2, "0")}`}
                        </div>
                      )}
                    </div>

                    {!readonly && (
                      <div className="flex flex-col space-y-2">
                        <button
                          onClick={() => handleSaveMapping(file.id)}
                          disabled={loading || !changed || !mapping?.requestId}
                          className={`px-3 py-2 text-sm rounded-md transition-colors ${
                            changed && mapping?.requestId
                              ? "bg-blue-100 text-blue-700 hover:bg-blue-200"
                              : "bg-gray-100 text-gray-400 cursor-not-allowed"
                          }`}
                        >
                          {loading ? "Saving..." : "Save"}
                        </button>

                        {mapping?.requestId && (
                          <button
                            onClick={() => handleClearMapping(file.id)}
                            className="px-3 py-2 text-sm bg-red-100 text-red-700 rounded-md hover:bg-red-200 transition-colors"
                          >
                            Clear
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Bulk Actions */}
        {!readonly && displayFiles.length > 0 && (
          <div className="mt-6 pt-4 border-t border-gray-200">
            <div className="flex justify-between items-center">
              <div className="text-sm text-gray-600">
                {mappings.filter((m) => hasChanges(m.fileId)).length} unsaved
                changes
              </div>
              <div className="flex space-x-3">
                <button
                  onClick={handleSaveAllMappings}
                  disabled={
                    loading || !mappings.some((m) => hasChanges(m.fileId))
                  }
                  className={`px-4 py-2 text-sm rounded-md transition-colors ${
                    mappings.some((m) => hasChanges(m.fileId))
                      ? "bg-green-100 text-green-700 hover:bg-green-200"
                      : "bg-gray-100 text-gray-400 cursor-not-allowed"
                  }`}
                >
                  {loading ? "Saving All..." : "Save All Changes"}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* File Type Summary */}
        {!showOnlyVideo && (
          <div className="mt-6 pt-4 border-t border-gray-200">
            <div className="text-sm text-gray-600">
              File types: {video.length} video, {subtitle.length} subtitle,{" "}
              {other.length} other
            </div>
          </div>
        )}

        {/* Available Requests Summary */}
        <div className="mt-6 pt-4 border-t border-gray-200">
          <div className="text-sm text-gray-600">
            Available requests: {movies.length} movies, {series.length} series
          </div>
        </div>
      </div>
    </div>
  );
};

export default FileRequestMapping;
