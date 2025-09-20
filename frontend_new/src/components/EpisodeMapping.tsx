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
    <div style={{ background: "transparent" }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: "1.5rem",
        }}
      >
        <div>
          <h3
            style={{
              fontSize: "1.25rem",
              fontWeight: "600",
              color: "#f1f5f9",
              margin: 0,
            }}
          >
            📺 Episode Mapping
          </h3>
          <p
            style={{
              fontSize: "0.875rem",
              color: "#94a3b8",
              marginTop: "0.25rem",
              margin: 0,
            }}
          >
            Map release files to specific episodes for series content.
          </p>
        </div>
      </div>

      <div>
        {/* Controls */}
        {!readonly && (
          <div style={{ marginBottom: "1.5rem" }}>
            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                alignItems: "center",
                gap: "1rem",
                marginBottom: "1rem",
              }}
            >
              <div
                style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}
              >
                <input
                  type="checkbox"
                  id="showOnlyVideo"
                  checked={showOnlyVideo}
                  onChange={(e) => setShowOnlyVideo(e.target.checked)}
                  style={{
                    accentColor: "#3b82f6",
                  }}
                />
                <label
                  htmlFor="showOnlyVideo"
                  style={{
                    fontSize: "0.875rem",
                    color: "#f1f5f9",
                  }}
                >
                  Show only video files ({video.length})
                </label>
              </div>

              <div
                style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}
              >
                <input
                  type="checkbox"
                  id="autoSuggest"
                  checked={autoSuggest}
                  onChange={(e) => setAutoSuggest(e.target.checked)}
                  style={{
                    accentColor: "#3b82f6",
                  }}
                />
                <label
                  htmlFor="autoSuggest"
                  style={{
                    fontSize: "0.875rem",
                    color: "#f1f5f9",
                  }}
                >
                  Auto-suggest from filenames
                </label>
              </div>

              <button
                onClick={handleAutoSuggest}
                className="btn btn-secondary"
                style={{
                  fontSize: "0.75rem",
                  padding: "0.5rem 0.75rem",
                }}
              >
                Re-suggest All
              </button>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
              <label
                style={{
                  fontSize: "0.875rem",
                  fontWeight: "600",
                  color: "#f1f5f9",
                }}
              >
                Bulk set season:
              </label>
              <div style={{ display: "flex", gap: "0.5rem" }}>
                {[1, 2, 3, 4, 5].map((season) => (
                  <button
                    key={season}
                    onClick={() => handleBulkSeasonUpdate(season)}
                    className="btn btn-secondary"
                    style={{
                      fontSize: "0.75rem",
                      padding: "0.25rem 0.5rem",
                    }}
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
          <div className="error" style={{ marginBottom: "1rem" }}>
            <div style={{ fontSize: "0.875rem" }}>{error}</div>
          </div>
        )}

        {/* Files List */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          {displayFiles.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">📁</div>
              <h3 className="empty-state-title">No files to map</h3>
              <p className="empty-state-description">
                No {showOnlyVideo ? "video " : ""}files available for mapping.
              </p>
            </div>
          ) : (
            displayFiles.map((file) => {
              const mapping = getFileMapping(file.id);
              const existing = getExistingMapping(file.id);
              const changed = hasChanges(file.id);

              return (
                <div
                  key={file.id}
                  className="card"
                  style={{
                    padding: "1rem",
                    background: existing
                      ? "rgba(34, 197, 94, 0.1)"
                      : "rgba(71, 85, 105, 0.2)",
                    border: existing
                      ? "1px solid rgba(34, 197, 94, 0.2)"
                      : "1px solid rgba(148, 163, 184, 0.1)",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      alignItems: "flex-start",
                      gap: "1rem",
                    }}
                  >
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "0.5rem",
                          marginBottom: "0.5rem",
                        }}
                      >
                        <span style={{ fontSize: "1.125rem" }}>
                          {isVideoFile(file.name) ? "🎬" : "📄"}
                        </span>
                        <h4
                          style={{
                            fontSize: "0.875rem",
                            fontWeight: "600",
                            color: "#f1f5f9",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                            flex: 1,
                          }}
                        >
                          {file.name}
                        </h4>
                        {existing && (
                          <span
                            style={{
                              padding: "0.25rem 0.5rem",
                              background: "rgba(34, 197, 94, 0.2)",
                              color: "#4ade80",
                              fontSize: "0.625rem",
                              borderRadius: "9999px",
                              border: "1px solid rgba(34, 197, 94, 0.3)",
                            }}
                          >
                            Mapped
                          </span>
                        )}
                        {changed && (
                          <span
                            style={{
                              padding: "0.25rem 0.5rem",
                              background: "rgba(251, 191, 36, 0.2)",
                              color: "#fbbf24",
                              fontSize: "0.625rem",
                              borderRadius: "9999px",
                              border: "1px solid rgba(251, 191, 36, 0.3)",
                            }}
                          >
                            Changed
                          </span>
                        )}
                      </div>

                      {existing && (
                        <div
                          style={{
                            fontSize: "0.875rem",
                            color: "#94a3b8",
                            marginBottom: "0.5rem",
                          }}
                        >
                          Current: {formatEpisodeTitle(existing)}
                        </div>
                      )}

                      {!readonly && mapping && (
                        <div
                          style={{
                            display: "grid",
                            gridTemplateColumns:
                              "repeat(auto-fit, minmax(120px, 1fr))",
                            gap: "0.75rem",
                          }}
                        >
                          <div>
                            <label
                              style={{
                                display: "block",
                                fontSize: "0.75rem",
                                fontWeight: "600",
                                color: "#f1f5f9",
                                marginBottom: "0.25rem",
                              }}
                            >
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
                              className="form-input"
                              style={{
                                width: "100%",
                                fontSize: "0.875rem",
                                padding: "0.5rem 0.75rem",
                              }}
                            />
                          </div>

                          <div>
                            <label
                              style={{
                                display: "block",
                                fontSize: "0.75rem",
                                fontWeight: "600",
                                color: "#f1f5f9",
                                marginBottom: "0.25rem",
                              }}
                            >
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
                              className="form-input"
                              style={{
                                width: "100%",
                                fontSize: "0.875rem",
                                padding: "0.5rem 0.75rem",
                              }}
                            />
                          </div>

                          <div style={{ gridColumn: "span 2" }}>
                            <label
                              style={{
                                display: "block",
                                fontSize: "0.75rem",
                                fontWeight: "600",
                                color: "#f1f5f9",
                                marginBottom: "0.25rem",
                              }}
                            >
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
                              className="form-input"
                              style={{
                                width: "100%",
                                fontSize: "0.875rem",
                                padding: "0.5rem 0.75rem",
                              }}
                            />
                          </div>
                        </div>
                      )}

                      {readonly && existing && (
                        <div
                          style={{
                            fontSize: "0.875rem",
                            color: "#f1f5f9",
                          }}
                        >
                          {formatEpisodeTitle(existing)}
                        </div>
                      )}

                      {mapping && (
                        <div
                          style={{
                            marginTop: "0.5rem",
                            fontSize: "0.75rem",
                            color: "#94a3b8",
                          }}
                        >
                          Preview: {formatEpisodeString(mapping)}
                          {mapping.title && ` - ${mapping.title}`}
                        </div>
                      )}
                    </div>

                    {!readonly && (
                      <div
                        style={{
                          display: "flex",
                          flexDirection: "column",
                          gap: "0.5rem",
                        }}
                      >
                        <button
                          onClick={() => handleSaveMapping(file.id)}
                          disabled={loading || !changed}
                          className={`btn ${
                            changed ? "btn-primary" : "btn-secondary"
                          }`}
                          style={{
                            fontSize: "0.75rem",
                            padding: "0.5rem 0.75rem",
                            opacity: changed ? 1 : 0.5,
                            cursor: changed ? "pointer" : "not-allowed",
                          }}
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
          <div
            style={{
              marginTop: "1.5rem",
              paddingTop: "1rem",
              borderTop: "1px solid rgba(148, 163, 184, 0.1)",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <div
                style={{
                  fontSize: "0.875rem",
                  color: "#94a3b8",
                }}
              >
                {mappings.filter((m) => hasChanges(m.fileId)).length} unsaved
                changes
              </div>
              <div style={{ display: "flex", gap: "0.75rem" }}>
                <button
                  onClick={handleSaveAllMappings}
                  disabled={
                    loading || !mappings.some((m) => hasChanges(m.fileId))
                  }
                  className={`btn ${
                    mappings.some((m) => hasChanges(m.fileId))
                      ? "btn-primary"
                      : "btn-secondary"
                  }`}
                  style={{
                    fontSize: "0.875rem",
                    padding: "0.5rem 1rem",
                    opacity: mappings.some((m) => hasChanges(m.fileId))
                      ? 1
                      : 0.5,
                    cursor: mappings.some((m) => hasChanges(m.fileId))
                      ? "pointer"
                      : "not-allowed",
                  }}
                >
                  {loading ? "Saving All..." : "Save All Changes"}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* File Type Summary */}
        {!showOnlyVideo && (
          <div
            style={{
              marginTop: "1.5rem",
              paddingTop: "1rem",
              borderTop: "1px solid rgba(148, 163, 184, 0.1)",
            }}
          >
            <div
              style={{
                fontSize: "0.875rem",
                color: "#94a3b8",
              }}
            >
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
