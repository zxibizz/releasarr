import React, { useState } from "react";
import { Link, useParams } from "react-router-dom";
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
  const [showFilesModal, setShowFilesModal] = useState(false);
  const [showMappingModal, setShowMappingModal] = useState(false);

  const handleViewFiles = (release: Release) => {
    setSelectedRelease(release);
    setShowFilesModal(true);
  };

  const handleEditMapping = (release: Release) => {
    setSelectedRelease(release);
    setShowMappingModal(true);
  };

  const closeModals = () => {
    setShowFilesModal(false);
    setShowMappingModal(false);
    setSelectedRelease(null);
  };

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner"></div>
        <span>Loading request...</span>
      </div>
    );
  }

  if (error || !request) {
    return (
      <div style={{ maxWidth: "32rem", margin: "0 auto" }}>
        <div className="error">
          <div>❌ Request not found</div>
          <p>{error || "The requested media could not be found."}</p>
          <Link to="/" className="btn btn-primary">
            ← Back to Requests
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="fade-in" style={{ maxWidth: "72rem", margin: "0 auto" }}>
      {/* Breadcrumb */}
      <nav style={{ marginBottom: "1.5rem" }}>
        <Link to="/" className="btn btn-outline">
          ← Back to Requests
        </Link>
      </nav>

      {/* Page Header */}
      <div className="page-header">
        <h1 className="page-title">{request.title}</h1>
        <p className="page-subtitle">
          {request.type === "movie" ? "Movie" : "TV Series"} Request Details
        </p>
      </div>

      {/* Media Information */}
      <div style={{ marginBottom: "2rem" }}>
        <MediaInfo request={request} />
      </div>

      {/* Torrent Search */}
      <div style={{ marginBottom: "2rem" }}>
        <TorrentSearch requestId={request.id} requestTitle={request.title} />
      </div>

      {/* Releases Section */}
      <div style={{ marginBottom: "2rem" }}>
        <div className="card">
          <h3
            style={{
              fontSize: "1.25rem",
              fontWeight: "600",
              color: "#f1f5f9",
              marginBottom: "1rem",
            }}
          >
            📦 Releases
          </h3>
          <p style={{ color: "#94a3b8", marginBottom: "1.5rem" }}>
            Torrent releases associated with this request
          </p>

          <ReleasesList
            requestId={request.id}
            onViewFiles={handleViewFiles}
            onEditMapping={handleEditMapping}
          />
        </div>
      </div>

      {/* Additional Actions */}
      <div className="card">
        <h3
          style={{
            fontSize: "1.25rem",
            fontWeight: "600",
            color: "#f1f5f9",
            marginBottom: "1rem",
          }}
        >
          🔧 Request Actions
        </h3>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))",
            gap: "1rem",
          }}
        >
          <button
            className="btn btn-secondary"
            style={{
              padding: "1rem",
              textAlign: "left",
              height: "auto",
              flexDirection: "column",
              alignItems: "flex-start",
            }}
            onClick={() =>
              alert("Refresh functionality would be implemented here")
            }
          >
            <div style={{ fontSize: "1.5rem", marginBottom: "0.5rem" }}>🔄</div>
            <div style={{ fontWeight: "600", marginBottom: "0.25rem" }}>
              Refresh Status
            </div>
            <div style={{ fontSize: "0.875rem", opacity: "0.8" }}>
              Check for updates on this request
            </div>
          </button>

          <button
            className="btn btn-secondary"
            style={{
              padding: "1rem",
              textAlign: "left",
              height: "auto",
              flexDirection: "column",
              alignItems: "flex-start",
            }}
            onClick={() =>
              alert("Manual search functionality would be implemented here")
            }
          >
            <div style={{ fontSize: "1.5rem", marginBottom: "0.5rem" }}>🔍</div>
            <div style={{ fontWeight: "600", marginBottom: "0.25rem" }}>
              Manual Search
            </div>
            <div style={{ fontSize: "0.875rem", opacity: "0.8" }}>
              Trigger a manual search for releases
            </div>
          </button>

          <button
            className="btn btn-secondary"
            style={{
              padding: "1rem",
              textAlign: "left",
              height: "auto",
              flexDirection: "column",
              alignItems: "flex-start",
            }}
            onClick={() =>
              alert("View logs functionality would be implemented here")
            }
          >
            <div style={{ fontSize: "1.5rem", marginBottom: "0.5rem" }}>📋</div>
            <div style={{ fontWeight: "600", marginBottom: "0.25rem" }}>
              View Logs
            </div>
            <div style={{ fontSize: "0.875rem", opacity: "0.8" }}>
              Check processing logs for this request
            </div>
          </button>
        </div>
      </div>

      {/* Files Modal */}
      {showFilesModal && selectedRelease && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(0, 0, 0, 0.8)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: "1rem",
          }}
          onClick={closeModals}
        >
          <div
            className="card"
            style={{
              maxWidth: "60rem",
              width: "100%",
              maxHeight: "80vh",
              overflow: "auto",
              margin: 0,
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                marginBottom: "1.5rem",
              }}
            >
              <h3
                style={{
                  fontSize: "1.25rem",
                  fontWeight: "600",
                  color: "#f1f5f9",
                  margin: 0,
                }}
              >
                📁 Files in {selectedRelease.name}
              </h3>
              <button
                onClick={closeModals}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "#94a3b8",
                  cursor: "pointer",
                  fontSize: "1.5rem",
                  padding: "0.25rem",
                  borderRadius: "0.25rem",
                }}
                onMouseOver={(e) => (e.currentTarget.style.color = "#f87171")}
                onMouseOut={(e) => (e.currentTarget.style.color = "#94a3b8")}
              >
                ✕
              </button>
            </div>

            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "0.75rem",
              }}
            >
              {selectedRelease.files.map((file, index) => (
                <div
                  key={index}
                  className="card"
                  style={{
                    padding: "1rem",
                    background: "rgba(71, 85, 105, 0.2)",
                    border: "1px solid rgba(148, 163, 184, 0.1)",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      alignItems: "flex-start",
                      justifyContent: "space-between",
                      gap: "1rem",
                    }}
                  >
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <h4
                        style={{
                          fontSize: "0.875rem",
                          fontWeight: "600",
                          color: "#f1f5f9",
                          marginBottom: "0.5rem",
                          wordBreak: "break-all",
                        }}
                      >
                        {file.name}
                      </h4>
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "1rem",
                          fontSize: "0.75rem",
                          color: "#94a3b8",
                          marginBottom: "0.5rem",
                        }}
                      >
                        <span>
                          Size: {(file.size / (1024 * 1024 * 1024)).toFixed(2)}{" "}
                          GB
                        </span>
                        <span>Progress: 100%</span>
                      </div>

                      {/* Episode Mapping Info */}
                      {file.episode_mapping && (
                        <div
                          style={{
                            padding: "0.5rem",
                            background: "rgba(59, 130, 246, 0.1)",
                            border: "1px solid rgba(59, 130, 246, 0.2)",
                            borderRadius: "0.25rem",
                            fontSize: "0.75rem",
                            color: "#93c5fd",
                            marginBottom: "0.5rem",
                          }}
                        >
                          📺 S
                          {file.episode_mapping.season
                            .toString()
                            .padStart(2, "0")}
                          E
                          {file.episode_mapping.episode
                            .toString()
                            .padStart(2, "0")}
                          {file.episode_mapping.title &&
                            ` - ${file.episode_mapping.title}`}
                        </div>
                      )}

                      {/* Request Mapping Info */}
                      {file.request_mapping && (
                        <div
                          style={{
                            padding: "0.5rem",
                            background: "rgba(139, 92, 246, 0.1)",
                            border: "1px solid rgba(139, 92, 246, 0.2)",
                            borderRadius: "0.25rem",
                            fontSize: "0.75rem",
                            color: "#c4b5fd",
                          }}
                        >
                          🔗 Mapped to request:{" "}
                          {file.request_mapping.request_id}
                          {file.request_mapping.request_title &&
                            ` (${file.request_mapping.request_title})`}
                        </div>
                      )}

                      {/* No mapping indicator */}
                      {!file.episode_mapping && !file.request_mapping && (
                        <div
                          style={{
                            padding: "0.5rem",
                            background: "rgba(251, 191, 36, 0.1)",
                            border: "1px solid rgba(251, 191, 36, 0.2)",
                            borderRadius: "0.25rem",
                            fontSize: "0.75rem",
                            color: "#fbbf24",
                          }}
                        >
                          ⚠️ No mapping configured
                        </div>
                      )}
                    </div>

                    {/* Progress Bar */}
                    <div style={{ width: "100px", textAlign: "right" }}>
                      <div
                        style={{
                          width: "100%",
                          background: "rgba(71, 85, 105, 0.3)",
                          borderRadius: "9999px",
                          height: "0.5rem",
                          marginBottom: "0.25rem",
                        }}
                      >
                        <div
                          style={{
                            background:
                              "linear-gradient(135deg, #4ade80, #22c55e)",
                            height: "0.5rem",
                            borderRadius: "9999px",
                            width: "100%",
                            transition: "all 0.3s ease",
                          }}
                        />
                      </div>
                      <div
                        style={{
                          fontSize: "0.75rem",
                          color: "#94a3b8",
                        }}
                      >
                        100%
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Mapping Modal */}
      {showMappingModal && selectedRelease && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(0, 0, 0, 0.8)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: "1rem",
          }}
          onClick={closeModals}
        >
          <div
            className="card"
            style={{
              maxWidth: "60rem",
              width: "100%",
              maxHeight: "80vh",
              overflow: "auto",
              margin: 0,
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                marginBottom: "1.5rem",
              }}
            >
              <h3
                style={{
                  fontSize: "1.25rem",
                  fontWeight: "600",
                  color: "#f1f5f9",
                  margin: 0,
                }}
              >
                🗺️ Map Files - {selectedRelease.name}
              </h3>
              <button
                onClick={closeModals}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "#94a3b8",
                  cursor: "pointer",
                  fontSize: "1.5rem",
                  padding: "0.25rem",
                  borderRadius: "0.25rem",
                }}
                onMouseOver={(e) => (e.currentTarget.style.color = "#f87171")}
                onMouseOut={(e) => (e.currentTarget.style.color = "#94a3b8")}
              >
                ✕
              </button>
            </div>

            {request.type === "series" ? (
              <EpisodeMapping
                releaseId={selectedRelease.id}
                files={selectedRelease.files}
                onClose={closeModals}
              />
            ) : (
              <FileRequestMapping
                releaseId={selectedRelease.id}
                files={selectedRelease.files}
                onClose={closeModals}
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
};
