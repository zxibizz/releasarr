import React, { useState } from "react";
import { Release } from "../types";
import {
  calculateReleaseProgress,
  formatFileSize,
  formatProgress,
  formatRatio,
  formatSpeed,
  getReleaseHealthScore,
  getStatusIcon,
  groupFilesByType,
  isReleaseActive,
} from "../utils/releaseHelpers";

interface ReleaseCardProps {
  release: Release;
  onPause?: (id: string) => void;
  onResume?: (id: string) => void;
  onDelete?: (id: string) => void;
  onViewFiles?: (release: Release) => void;
  onEditMapping?: (release: Release) => void;
  showActions?: boolean;
  compact?: boolean;
}

const ReleaseCard: React.FC<ReleaseCardProps> = ({
  release,
  onPause,
  onResume,
  onDelete,
  onViewFiles,
  onEditMapping,
  showActions = true,
  compact = false,
}) => {
  const [showDetails, setShowDetails] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const progress = calculateReleaseProgress(release);
  const isActive = isReleaseActive(release);
  const healthScore = getReleaseHealthScore(release);
  const { video, subtitle, other } = groupFilesByType(release.files);

  const handleAction = async (action: () => Promise<void> | void) => {
    setIsLoading(true);
    try {
      await action();
    } catch (error) {
      console.error("Action failed:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case "downloading":
        return "status-badge pending";
      case "seeding":
        return "status-badge approved";
      case "completed":
        return "status-badge completed";
      case "failed":
        return "status-badge rejected";
      default:
        return "status-badge pending";
    }
  };

  if (compact) {
    return (
      <div className="card" style={{ padding: "1rem" }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div style={{ flex: 1, minWidth: 0 }}>
            <div
              style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}
            >
              <span style={{ fontSize: "1.125rem" }}>
                {getStatusIcon(release.status)}
              </span>
              <h3
                style={{
                  fontSize: "0.875rem",
                  fontWeight: "600",
                  color: "#f1f5f9",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {release.name}
              </h3>
            </div>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "1rem",
                marginTop: "0.25rem",
                fontSize: "0.75rem",
                color: "#94a3b8",
              }}
            >
              <span>{formatFileSize(release.size)}</span>
              <span
                className={getStatusBadgeClass(release.status)}
                style={{
                  padding: "0.125rem 0.5rem",
                  fontSize: "0.625rem",
                }}
              >
                {release.status}
              </span>
              {isActive && <span>{formatProgress(progress)}</span>}
            </div>
          </div>
          {showActions && (
            <div
              style={{ display: "flex", alignItems: "center", gap: "0.25rem" }}
            >
              <button
                onClick={() => onViewFiles?.(release)}
                style={{
                  padding: "0.25rem",
                  background: "transparent",
                  border: "none",
                  color: "#94a3b8",
                  cursor: "pointer",
                  borderRadius: "0.25rem",
                  transition: "color 0.2s ease",
                }}
                onMouseOver={(e) => (e.currentTarget.style.color = "#cbd5e1")}
                onMouseOut={(e) => (e.currentTarget.style.color = "#94a3b8")}
                title="View files"
              >
                📁
              </button>
              <button
                onClick={() => setShowDetails(!showDetails)}
                style={{
                  padding: "0.25rem",
                  background: "transparent",
                  border: "none",
                  color: "#94a3b8",
                  cursor: "pointer",
                  borderRadius: "0.25rem",
                  transition: "color 0.2s ease",
                }}
                onMouseOver={(e) => (e.currentTarget.style.color = "#cbd5e1")}
                onMouseOut={(e) => (e.currentTarget.style.color = "#94a3b8")}
                title="Toggle details"
              >
                {showDetails ? "▲" : "▼"}
              </button>
            </div>
          )}
        </div>

        {showDetails && (
          <div
            style={{
              marginTop: "1rem",
              paddingTop: "1rem",
              borderTop: "1px solid rgba(148, 163, 184, 0.1)",
              fontSize: "0.75rem",
              color: "#94a3b8",
            }}
          >
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "0.5rem",
                marginBottom: "0.5rem",
              }}
            >
              <div>Seeders: {release.seeders}</div>
              <div>Leechers: {release.leechers}</div>
              <div>Ratio: {formatRatio(release.ratio)}</div>
              <div>
                Health:{" "}
                <span
                  style={{
                    color:
                      healthScore > 70
                        ? "#4ade80"
                        : healthScore > 40
                        ? "#fbbf24"
                        : "#f87171",
                  }}
                >
                  {healthScore}%
                </span>
              </div>
            </div>
            {isActive && (
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: "0.5rem",
                }}
              >
                <div>↓ {formatSpeed(release.download_speed)}</div>
                <div>↑ {formatSpeed(release.upload_speed)}</div>
              </div>
            )}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="card">
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
        }}
      >
        <div style={{ flex: 1, minWidth: 0 }}>
          <div
            style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}
          >
            <span style={{ fontSize: "1.5rem" }}>
              {getStatusIcon(release.status)}
            </span>
            <div>
              <h3
                style={{
                  fontSize: "1.125rem",
                  fontWeight: "600",
                  color: "#f1f5f9",
                  marginBottom: "0.25rem",
                }}
              >
                {release.name}
              </h3>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "1rem",
                  marginTop: "0.25rem",
                }}
              >
                <span className={getStatusBadgeClass(release.status)}>
                  {release.status}
                </span>
                <span style={{ fontSize: "0.875rem", color: "#94a3b8" }}>
                  {formatFileSize(release.size)}
                </span>
                {release.quality && (
                  <span
                    style={{
                      fontSize: "0.875rem",
                      color: "#94a3b8",
                      background: "rgba(71, 85, 105, 0.3)",
                      padding: "0.25rem 0.5rem",
                      borderRadius: "0.25rem",
                    }}
                  >
                    {release.quality}
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Progress Bar */}
          {isActive && (
            <div style={{ marginTop: "1rem" }}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  fontSize: "0.875rem",
                  color: "#94a3b8",
                  marginBottom: "0.25rem",
                }}
              >
                <span>Progress</span>
                <span>{formatProgress(progress)}</span>
              </div>
              <div
                style={{
                  width: "100%",
                  background: "rgba(71, 85, 105, 0.3)",
                  borderRadius: "9999px",
                  height: "0.5rem",
                }}
              >
                <div
                  style={{
                    background: "linear-gradient(135deg, #3b82f6, #8b5cf6)",
                    height: "0.5rem",
                    borderRadius: "9999px",
                    transition: "all 0.3s ease",
                    width: `${progress}%`,
                  }}
                />
              </div>
            </div>
          )}

          {/* Stats Grid */}
          <div
            style={{
              marginTop: "1rem",
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))",
              gap: "1rem",
            }}
          >
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: "0.75rem", color: "#94a3b8" }}>
                Seeders
              </div>
              <div
                style={{
                  fontSize: "1.125rem",
                  fontWeight: "600",
                  color: "#4ade80",
                }}
              >
                {release.seeders}
              </div>
            </div>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: "0.75rem", color: "#94a3b8" }}>
                Leechers
              </div>
              <div
                style={{
                  fontSize: "1.125rem",
                  fontWeight: "600",
                  color: "#3b82f6",
                }}
              >
                {release.leechers}
              </div>
            </div>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: "0.75rem", color: "#94a3b8" }}>Ratio</div>
              <div
                style={{
                  fontSize: "1.125rem",
                  fontWeight: "600",
                  color: "#8b5cf6",
                }}
              >
                {formatRatio(release.ratio)}
              </div>
            </div>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: "0.75rem", color: "#94a3b8" }}>
                Health
              </div>
              <div
                style={{
                  fontSize: "1.125rem",
                  fontWeight: "600",
                  color:
                    healthScore > 70
                      ? "#4ade80"
                      : healthScore > 40
                      ? "#fbbf24"
                      : "#f87171",
                }}
              >
                {healthScore}%
              </div>
            </div>
          </div>

          {/* Speed Info */}
          {(release.download_speed > 0 || release.upload_speed > 0) && (
            <div
              style={{
                marginTop: "1rem",
                display: "flex",
                alignItems: "center",
                gap: "1.5rem",
              }}
            >
              {release.download_speed > 0 && (
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "0.5rem",
                  }}
                >
                  <span style={{ color: "#3b82f6" }}>↓</span>
                  <span
                    style={{
                      fontSize: "0.875rem",
                      fontWeight: "500",
                      color: "#f1f5f9",
                    }}
                  >
                    {formatSpeed(release.download_speed)}
                  </span>
                </div>
              )}
              {release.upload_speed > 0 && (
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "0.5rem",
                  }}
                >
                  <span style={{ color: "#4ade80" }}>↑</span>
                  <span
                    style={{
                      fontSize: "0.875rem",
                      fontWeight: "500",
                      color: "#f1f5f9",
                    }}
                  >
                    {formatSpeed(release.upload_speed)}
                  </span>
                </div>
              )}
            </div>
          )}

          {/* File Info */}
          <div
            style={{
              marginTop: "1rem",
              display: "flex",
              alignItems: "center",
              gap: "1rem",
              fontSize: "0.875rem",
              color: "#94a3b8",
            }}
          >
            <span>📁 {release.files.length} files</span>
            {video.length > 0 && <span>🎬 {video.length} video</span>}
            {subtitle.length > 0 && <span>📝 {subtitle.length} subtitle</span>}
            {other.length > 0 && <span>📄 {other.length} other</span>}
          </div>

          {/* Dates */}
          <div
            style={{
              marginTop: "1rem",
              display: "flex",
              alignItems: "center",
              gap: "1rem",
              fontSize: "0.875rem",
              color: "#64748b",
            }}
          >
            <span>Added: {formatDate(release.added_date)}</span>
            {release.completed_date && (
              <span>Completed: {formatDate(release.completed_date)}</span>
            )}
          </div>

          {/* Request IDs */}
          {release.request_ids.length > 0 && (
            <div style={{ marginTop: "1rem" }}>
              <div
                style={{
                  fontSize: "0.875rem",
                  color: "#94a3b8",
                  marginBottom: "0.5rem",
                }}
              >
                Related Requests:
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
                {release.request_ids.map((requestId) => (
                  <span
                    key={requestId}
                    style={{
                      padding: "0.25rem 0.5rem",
                      background: "rgba(59, 130, 246, 0.2)",
                      color: "#93c5fd",
                      fontSize: "0.75rem",
                      borderRadius: "9999px",
                      border: "1px solid rgba(59, 130, 246, 0.3)",
                    }}
                  >
                    {requestId}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Actions */}
        {showActions && (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "0.5rem",
              marginLeft: "1rem",
            }}
          >
            <button
              onClick={() => onViewFiles?.(release)}
              className="btn btn-secondary"
              style={{ fontSize: "0.75rem", padding: "0.5rem 0.75rem" }}
              disabled={isLoading}
            >
              View Files
            </button>

            {release.files.some(
              (f) => !f.episode_mapping && !f.request_mapping
            ) && (
              <button
                onClick={() => onEditMapping?.(release)}
                className="btn"
                style={{
                  fontSize: "0.75rem",
                  padding: "0.5rem 0.75rem",
                  background: "rgba(251, 191, 36, 0.2)",
                  color: "#fbbf24",
                  border: "1px solid rgba(251, 191, 36, 0.3)",
                }}
                disabled={isLoading}
              >
                Map Files
              </button>
            )}

            {isActive && onPause && (
              <button
                onClick={() => handleAction(() => onPause(release.id))}
                className="btn"
                style={{
                  fontSize: "0.75rem",
                  padding: "0.5rem 0.75rem",
                  background: "rgba(251, 146, 60, 0.2)",
                  color: "#fb923c",
                  border: "1px solid rgba(251, 146, 60, 0.3)",
                }}
                disabled={isLoading}
              >
                Pause
              </button>
            )}

            {release.status === "pending" && onResume && (
              <button
                onClick={() => handleAction(() => onResume(release.id))}
                className="btn"
                style={{
                  fontSize: "0.75rem",
                  padding: "0.5rem 0.75rem",
                  background: "rgba(34, 197, 94, 0.2)",
                  color: "#4ade80",
                  border: "1px solid rgba(34, 197, 94, 0.3)",
                }}
                disabled={isLoading}
              >
                Resume
              </button>
            )}

            {onDelete && (
              <button
                onClick={() => handleAction(() => onDelete(release.id))}
                className="btn"
                style={{
                  fontSize: "0.75rem",
                  padding: "0.5rem 0.75rem",
                  background: "rgba(239, 68, 68, 0.2)",
                  color: "#f87171",
                  border: "1px solid rgba(239, 68, 68, 0.3)",
                }}
                disabled={isLoading}
              >
                Delete
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default ReleaseCard;
