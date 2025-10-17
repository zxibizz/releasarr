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
  onClose,
  readonly = false,
}) => {
  const { updateFileMapping, loading, error } = useReleaseFileMapping();
  const [mappings, setMappings] = useState<FileMapping[]>([]);
  const [autoSuggest, setAutoSuggest] = useState(true);
  const [showOnlyVideo, setShowOnlyVideo] = useState(true);

  const { video, subtitle, other } = groupFilesByType(files);
  const displayFiles = showOnlyVideo ? video : files;

  useEffect(() => {
    // Initialize mappings from existing data or suggestions
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
      alert(
        "Invalid episode mapping. Please check season and episode numbers."
      );
      return;
    }

    try {
      await updateFileMapping(releaseId, fileId, {
        episode_mapping: episodeMapping,
      });
      onMappingUpdate?.(fileId, episodeMapping);
    } catch (error) {
      console.error("Failed to update mapping:", error);
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
        } catch (error) {
          console.error(
            `Failed to update mapping for ${mapping.fileId}:`,
            error
          );
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

  const getFileMapping = (fileId: string) => {
    return mappings.find((m) => m.fileId === fileId);
  };

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
    <div className="bg-white rounded-lg shadow-lg border border-gray-200">
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900">
            Episode Mapping
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
          Map release files to specific episodes for series content.
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

              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="autoSuggest"
                  checked={autoSuggest}
                  onChange={(e) => setAutoSuggest(e.target.checked)}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <label htmlFor="autoSuggest" className="text-sm text-gray-700">
                  Auto-suggest from filenames
                </label>
              </div>

              <button
                onClick={handleAutoSuggest}
                className="px-3 py-2 bg-blue-100 text-blue-700 text-sm rounded-md hover:bg-blue-200 transition-colors"
              >
                Re-suggest All
              </button>
            </div>

            <div className="flex items-center space-x-4">
              <label className="text-sm font-medium text-gray-700">
                Bulk set season:
              </label>
              <div className="flex space-x-2">
                {[1, 2, 3, 4, 5].map((season) => (
                  <button
                    key={season}
                    onClick={() => handleBulkSeasonUpdate(season)}
                    className="px-3 py-1 bg-gray-100 text-gray-700 text-sm rounded-md hover:bg-gray-200 transition-colors"
                  >
                    S{season.toString().padStart(2, "0")}
                  </button>
                ))}
              </div>
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
                      ? "border-green-200 bg-green-50"
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
                        {existing && (
                          <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full">
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
                          Current: {formatEpisodeTitle(existing)}
                        </div>
                      )}

                      {!readonly && mapping && (
                        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                          <div>
                            <label className="block text-xs font-medium text-gray-700 mb-1">
                              Season
                            </label>
                            <input
                              type="number"
                              min="1"
                              max="99"
                              value={mapping.season}
                              onChange={(e) =>
                                handleMappingChange(
                                  file.id,
                                  "season",
                                  parseInt(e.target.value) || 1
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
                              value={mapping.episode}
                              onChange={(e) =>
                                handleMappingChange(
                                  file.id,
                                  "episode",
                                  parseInt(e.target.value) || 1
                                )
                              }
                              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                            />
                          </div>

                          <div className="md:col-span-2">
                            <label className="block text-xs font-medium text-gray-700 mb-1">
                              Title (optional)
                            </label>
                            <input
                              type="text"
                              value={mapping.title}
                              onChange={(e) =>
                                handleMappingChange(
                                  file.id,
                                  "title",
                                  e.target.value
                                )
                              }
                              placeholder="Episode title"
                              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                            />
                          </div>
                        </div>
                      )}

                      {readonly && existing && (
                        <div className="text-sm text-gray-900">
                          {formatEpisodeTitle(existing)}
                        </div>
                      )}

                      {mapping && (
                        <div className="mt-2 text-xs text-gray-500">
                          Preview: {formatEpisodeString(mapping)}
                          {mapping.title && ` - ${mapping.title}`}
                        </div>
                      )}
                    </div>

                    {!readonly && (
                      <div className="flex flex-col space-y-2">
                        <button
                          onClick={() => handleSaveMapping(file.id)}
                          disabled={loading || !changed}
                          className={`px-3 py-2 text-sm rounded-md transition-colors ${
                            changed
                              ? "bg-blue-100 text-blue-700 hover:bg-blue-200"
                              : "bg-gray-100 text-gray-400 cursor-not-allowed"
                          }`}
                        >
                          {loading ? "Saving..." : "Save"}
                        </button>
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
      </div>
    </div>
  );
};

export default EpisodeMapping;
