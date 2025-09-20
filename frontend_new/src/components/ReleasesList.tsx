import React, { useMemo, useState } from "react";
import { useReleasesByRequest } from "../hooks/useReleases";
import { Release } from "../types";
import {
  filterReleasesByStatus,
  formatSpeed,
  getActiveDownloads,
  getCompletedReleases,
  getTotalDownloadSpeed,
  getTotalUploadSpeed,
  sortReleasesByDate,
  sortReleasesBySize,
  sortReleasesByStatus,
} from "../utils/releaseHelpers";
import ReleaseCard from "./ReleaseCard";

interface ReleasesListProps {
  requestId: string;
  onPauseRelease?: (id: string) => void;
  onResumeRelease?: (id: string) => void;
  onDeleteRelease?: (id: string) => void;
  onViewFiles?: (release: Release) => void;
  onEditMapping?: (release: Release) => void;
  compact?: boolean;
  showStats?: boolean;
}

type SortOption = "status" | "date" | "size";
type FilterOption =
  | "all"
  | "downloading"
  | "pending"
  | "seeding"
  | "completed"
  | "failed";

const ReleasesList: React.FC<ReleasesListProps> = ({
  requestId,
  onPauseRelease,
  onResumeRelease,
  onDeleteRelease,
  onViewFiles,
  onEditMapping,
  compact = false,
  showStats = true,
}) => {
  const { releases, loading, error, refetch } = useReleasesByRequest(requestId);
  const [sortBy, setSortBy] = useState<SortOption>("status");
  const [filterBy, setFilterBy] = useState<FilterOption>("all");
  const [sortAscending, setSortAscending] = useState(false);

  const filteredAndSortedReleases = useMemo(() => {
    let filtered = releases;

    // Apply filter
    if (filterBy !== "all") {
      filtered = filterReleasesByStatus(
        releases,
        filterBy as Release["status"]
      );
    }

    // Apply sort
    switch (sortBy) {
      case "status":
        return sortReleasesByStatus(filtered);
      case "date":
        return sortReleasesByDate(filtered, sortAscending);
      case "size":
        return sortReleasesBySize(filtered, sortAscending);
      default:
        return filtered;
    }
  }, [releases, sortBy, filterBy, sortAscending]);

  const stats = useMemo(() => {
    const activeDownloads = getActiveDownloads(releases);
    const completedReleases = getCompletedReleases(releases);
    const totalDownloadSpeed = getTotalDownloadSpeed(releases);
    const totalUploadSpeed = getTotalUploadSpeed(releases);

    return {
      total: releases.length,
      active: activeDownloads.length,
      completed: completedReleases.length,
      downloadSpeed: totalDownloadSpeed,
      uploadSpeed: totalUploadSpeed,
    };
  }, [releases]);

  const handleSortChange = (newSort: SortOption) => {
    if (sortBy === newSort) {
      setSortAscending(!sortAscending);
    } else {
      setSortBy(newSort);
      setSortAscending(false);
    }
  };

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner"></div>
        <span>Loading releases...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="error">
        <div style={{ display: "flex", alignItems: "center" }}>
          <div style={{ marginRight: "0.5rem" }}>❌</div>
          <div>
            <h3
              style={{
                fontSize: "0.875rem",
                fontWeight: "600",
                marginBottom: "0.25rem",
              }}
            >
              Error loading releases
            </h3>
            <p style={{ fontSize: "0.875rem", margin: 0 }}>{error}</p>
          </div>
        </div>
        <button
          onClick={refetch}
          className="btn btn-secondary"
          style={{
            marginTop: "0.75rem",
            fontSize: "0.75rem",
            padding: "0.5rem 0.75rem",
          }}
        >
          Try Again
        </button>
      </div>
    );
  }

  if (releases.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">📦</div>
        <h3 className="empty-state-title">No releases found</h3>
        <p className="empty-state-description">
          No torrent releases have been added for this request yet.
        </p>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      {/* Stats */}
      {showStats && (
        <div className="card" style={{ padding: "1rem" }}>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))",
              gap: "1rem",
              textAlign: "center",
            }}
          >
            <div>
              <div
                style={{
                  fontSize: "1.5rem",
                  fontWeight: "700",
                  color: "#3b82f6",
                }}
              >
                {stats.total}
              </div>
              <div style={{ fontSize: "0.875rem", color: "#94a3b8" }}>
                Total
              </div>
            </div>
            <div>
              <div
                style={{
                  fontSize: "1.5rem",
                  fontWeight: "700",
                  color: "#fb923c",
                }}
              >
                {stats.active}
              </div>
              <div style={{ fontSize: "0.875rem", color: "#94a3b8" }}>
                Active
              </div>
            </div>
            <div>
              <div
                style={{
                  fontSize: "1.5rem",
                  fontWeight: "700",
                  color: "#4ade80",
                }}
              >
                {stats.completed}
              </div>
              <div style={{ fontSize: "0.875rem", color: "#94a3b8" }}>
                Completed
              </div>
            </div>
            <div>
              <div
                style={{
                  fontSize: "1.125rem",
                  fontWeight: "700",
                  color: "#3b82f6",
                }}
              >
                {formatSpeed(stats.downloadSpeed)}
              </div>
              <div style={{ fontSize: "0.875rem", color: "#94a3b8" }}>
                Download
              </div>
            </div>
            <div>
              <div
                style={{
                  fontSize: "1.125rem",
                  fontWeight: "700",
                  color: "#4ade80",
                }}
              >
                {formatSpeed(stats.uploadSpeed)}
              </div>
              <div style={{ fontSize: "0.875rem", color: "#94a3b8" }}>
                Upload
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Controls */}
      <div className="card" style={{ padding: "1rem" }}>
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "1rem",
          }}
        >
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              alignItems: "center",
              justifyContent: "space-between",
              gap: "1rem",
            }}
          >
            {/* Filter */}
            <div
              style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}
            >
              <label
                style={{
                  fontSize: "0.875rem",
                  fontWeight: "600",
                  color: "#f1f5f9",
                }}
              >
                Filter:
              </label>
              <select
                value={filterBy}
                onChange={(e) => setFilterBy(e.target.value as FilterOption)}
                className="form-select"
                style={{
                  minWidth: "150px",
                  fontSize: "0.875rem",
                  padding: "0.5rem 0.75rem",
                }}
              >
                <option value="all">All ({releases.length})</option>
                <option value="downloading">
                  Downloading (
                  {filterReleasesByStatus(releases, "downloading").length})
                </option>
                <option value="pending">
                  Pending ({filterReleasesByStatus(releases, "pending").length})
                </option>
                <option value="seeding">
                  Seeding ({filterReleasesByStatus(releases, "seeding").length})
                </option>
                <option value="completed">
                  Completed (
                  {filterReleasesByStatus(releases, "completed").length})
                </option>
                <option value="failed">
                  Failed ({filterReleasesByStatus(releases, "failed").length})
                </option>
              </select>
            </div>

            {/* Sort */}
            <div
              style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}
            >
              <label
                style={{
                  fontSize: "0.875rem",
                  fontWeight: "600",
                  color: "#f1f5f9",
                }}
              >
                Sort by:
              </label>
              <div style={{ display: "flex", gap: "0.25rem" }}>
                <button
                  onClick={() => handleSortChange("status")}
                  className={`btn ${
                    sortBy === "status" ? "btn-primary" : "btn-secondary"
                  }`}
                  style={{ fontSize: "0.75rem", padding: "0.5rem 0.75rem" }}
                >
                  Status {sortBy === "status" && (sortAscending ? "↑" : "↓")}
                </button>
                <button
                  onClick={() => handleSortChange("date")}
                  className={`btn ${
                    sortBy === "date" ? "btn-primary" : "btn-secondary"
                  }`}
                  style={{ fontSize: "0.75rem", padding: "0.5rem 0.75rem" }}
                >
                  Date {sortBy === "date" && (sortAscending ? "↑" : "↓")}
                </button>
                <button
                  onClick={() => handleSortChange("size")}
                  className={`btn ${
                    sortBy === "size" ? "btn-primary" : "btn-secondary"
                  }`}
                  style={{ fontSize: "0.75rem", padding: "0.5rem 0.75rem" }}
                >
                  Size {sortBy === "size" && (sortAscending ? "↑" : "↓")}
                </button>
              </div>
            </div>

            {/* Refresh */}
            <button
              onClick={refetch}
              className="btn btn-secondary"
              style={{ fontSize: "0.75rem", padding: "0.5rem 0.75rem" }}
            >
              🔄 Refresh
            </button>
          </div>
        </div>
      </div>

      {/* Results count */}
      {filterBy !== "all" && (
        <div style={{ fontSize: "0.875rem", color: "#94a3b8" }}>
          Showing {filteredAndSortedReleases.length} of {releases.length}{" "}
          releases
        </div>
      )}

      {/* Releases List */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: compact ? "0.5rem" : "1rem",
        }}
      >
        {filteredAndSortedReleases.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">🔍</div>
            <h3 className="empty-state-title">No releases match your filter</h3>
            <p className="empty-state-description">
              Try adjusting your filter criteria to see more results.
            </p>
            <button
              onClick={() => setFilterBy("all")}
              className="btn btn-primary"
              style={{ marginTop: "0.75rem", fontSize: "0.875rem" }}
            >
              Show All Releases
            </button>
          </div>
        ) : (
          filteredAndSortedReleases.map((release) => (
            <ReleaseCard
              key={release.id}
              release={release}
              onPause={onPauseRelease}
              onResume={onResumeRelease}
              onDelete={onDeleteRelease}
              onViewFiles={onViewFiles}
              onEditMapping={onEditMapping}
              compact={compact}
            />
          ))
        )}
      </div>
    </div>
  );
};

export default ReleasesList;
