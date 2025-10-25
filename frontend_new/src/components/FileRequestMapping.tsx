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
            🔗 File Request Mapping
          </h3>
          <p
            style={{
              fontSize: "0.875rem",
              color: "#94a3b8",
              marginTop: "0.25rem",
              margin: 0,
            }}
          >
            Map release files to specific requests for cross-request
            collections.
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
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
              <label
                style={{
                  fontSize: "0.875rem",
                  fontWeight: "600",
                  color: "#f1f5f9",
                }}
              >
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
                className="form-select"
                style={{
                  minWidth: "200px",
                  fontSize: "0.875rem",
                  padding: "0.5rem 0.75rem",
                }}
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
                      ? "rgba(59, 130, 246, 0.1)"
                      : "rgba(71, 85, 105, 0.2)",
                    border: existing
                      ? "1px solid rgba(59, 130, 246, 0.2)"
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
                        <span
                          style={{
                            fontSize: "0.75rem",
                            color: "#94a3b8",
                          }}
                        >
                          ({formatFileSize(file.size)})
                        </span>
                        {existing && (
                          <span
                            style={{
                              padding: "0.25rem 0.5rem",
                              background: "rgba(59, 130, 246, 0.2)",
                              color: "#3b82f6",
                              fontSize: "0.625rem",
                              borderRadius: "9999px",
                              border: "1px solid rgba(59, 130, 246, 0.3)",
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
                        <div
                          style={{
                            display: "flex",
                            flexDirection: "column",
                            gap: "0.75rem",
                          }}
                        >
                          {/* Request Selection */}
                          <div
                            style={{
                              display: "grid",
                              gridTemplateColumns: "1fr 1fr",
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
                                className="form-select"
                                style={{
                                  width: "100%",
                                  fontSize: "0.875rem",
                                  padding: "0.5rem 0.75rem",
                                }}
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
                              <label
                                style={{
                                  display: "block",
                                  fontSize: "0.75rem",
                                  fontWeight: "600",
                                  color: "#f1f5f9",
                                  marginBottom: "0.25rem",
                                }}
                              >
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
                                className="form-select"
                                style={{
                                  width: "100%",
                                  fontSize: "0.875rem",
                                  padding: "0.5rem 0.75rem",
                                }}
                              >
                                <option value="movie">Movie</option>
                                <option value="episode">Episode</option>
                                <option value="season">Season</option>
                              </select>
                            </div>
                          </div>

                          {/* Episode Details (for series) */}
                          {mapping.mappingType === "episode" && (
                            <div
                              style={{
                                display: "grid",
                                gridTemplateColumns: "1fr 1fr",
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

                          {mapping.mappingType === "season" && (
                            <div
                              style={{
                                display: "grid",
                                gridTemplateColumns: "1fr",
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
                        </div>
                      )}

                      {readonly && existing && (
                        <div
                          style={{
                            fontSize: "0.875rem",
                            color: "#f1f5f9",
                          }}
                        >
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
                      <div
                        style={{
                          display: "flex",
                          flexDirection: "column",
                          gap: "0.5rem",
                        }}
                      >
                        <button
                          onClick={() => handleSaveMapping(file.id)}
                          disabled={loading || !changed || !mapping?.requestId}
                          className={`btn ${
                            changed && mapping?.requestId
                              ? "btn-primary"
                              : "btn-secondary"
                          }`}
                          style={{
                            fontSize: "0.75rem",
                            padding: "0.5rem 0.75rem",
                            opacity: changed && mapping?.requestId ? 1 : 0.5,
                            cursor:
                              changed && mapping?.requestId
                                ? "pointer"
                                : "not-allowed",
                          }}
                        >
                          {loading ? "Saving..." : "Save"}
                        </button>

                        {mapping?.requestId && (
                          <button
                            onClick={() => handleClearMapping(file.id)}
                            className="btn"
                            style={{
                              fontSize: "0.75rem",
                              padding: "0.5rem 0.75rem",
                              background: "rgba(239, 68, 68, 0.2)",
                              color: "#f87171",
                              border: "1px solid rgba(239, 68, 68, 0.3)",
                            }}
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

        {/* Available Requests Summary */}
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
            Available requests: {movies.length} movies, {series.length} series
          </div>
        </div>
      </div>
    </div>
  );
};

export default FileRequestMapping;
