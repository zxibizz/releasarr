import React, { useState } from "react";
import { useTorrentSearch } from "../hooks/useTorrentSearch";
import { TorrentResult } from "../types";

interface TorrentSearchProps {
  requestId: string;
  requestTitle: string;
}

export const TorrentSearch: React.FC<TorrentSearchProps> = ({
  requestId,
  requestTitle,
}) => {
  const { searchState, search, clearSearch, selectTorrent } =
    useTorrentSearch();
  const [query, setQuery] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      search(query.trim());
    }
  };

  const handleClear = () => {
    setQuery("");
    clearSearch();
  };

  const handleTorrentSelect = (torrent: TorrentResult) => {
    selectTorrent(torrent);
    // In a real app, this would trigger the download process
    alert(`Selected torrent: ${torrent.name}`);
  };

  return (
    <div className="card">
      <h3
        style={{
          fontSize: "1.25rem",
          fontWeight: "600",
          color: "#f1f5f9",
          marginBottom: "1rem",
        }}
      >
        🔍 Search Torrents
      </h3>

      {/* Search Form */}
      <form onSubmit={handleSubmit} className="form-group">
        <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
          <div style={{ flex: "1", minWidth: "200px" }}>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={`Search torrents for "${requestTitle}"...`}
              className="form-input"
            />
          </div>
          <button
            type="submit"
            disabled={!query.trim() || searchState.loading}
            className="btn btn-primary"
          >
            {searchState.loading ? "Searching..." : "Search"}
          </button>
          {(query || searchState.results.length > 0) && (
            <button
              type="button"
              onClick={handleClear}
              className="btn btn-secondary"
            >
              Clear
            </button>
          )}
        </div>
      </form>

      {/* Loading State */}
      {searchState.loading && (
        <div className="loading">
          <div className="spinner"></div>
          <span>Searching torrents...</span>
        </div>
      )}

      {/* Error State */}
      {searchState.error && (
        <div className="error" style={{ marginBottom: "1.5rem" }}>
          ❌ {searchState.error}
        </div>
      )}

      {/* Results */}
      {searchState.results.length > 0 && !searchState.loading && (
        <div className="torrent-results">
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "1rem",
            }}
          >
            <h4
              style={{
                fontSize: "1.125rem",
                fontWeight: "600",
                color: "#f1f5f9",
              }}
            >
              Search Results
            </h4>
            <span style={{ color: "#94a3b8", fontSize: "0.875rem" }}>
              {searchState.results.length} results for "{searchState.query}"
            </span>
          </div>

          <div>
            {searchState.results.map((torrent) => (
              <div key={torrent.id} className="torrent-item">
                <div className="torrent-info">
                  <div className="torrent-name">{torrent.name}</div>
                  <div className="torrent-meta">
                    <span
                      style={{
                        padding: "0.25rem 0.5rem",
                        borderRadius: "0.25rem",
                        fontSize: "0.75rem",
                        fontWeight: "600",
                        background: getQualityBadgeStyle(torrent.quality)
                          .background,
                        color: getQualityBadgeStyle(torrent.quality).color,
                        border: `1px solid ${
                          getQualityBadgeStyle(torrent.quality).border
                        }`,
                      }}
                    >
                      {torrent.quality}
                    </span>
                    <span>📦 {torrent.size}</span>
                    <span style={{ color: "#4ade80" }}>
                      ⬆️ {torrent.seeders}
                    </span>
                    <span style={{ color: "#f87171" }}>
                      ⬇️ {torrent.leechers}
                    </span>
                    <span>🏷️ {torrent.source}</span>
                  </div>
                </div>
                <div className="torrent-actions">
                  <button
                    onClick={() => handleTorrentSelect(torrent)}
                    className="btn btn-primary"
                    style={{ fontSize: "0.875rem" }}
                  >
                    Select
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* No Results */}
      {searchState.query &&
        searchState.results.length === 0 &&
        !searchState.loading &&
        !searchState.error && (
          <div className="empty-state">
            <div className="empty-state-icon">🔍</div>
            <h4 className="empty-state-title">No torrents found</h4>
            <p className="empty-state-description">
              Try adjusting your search terms or check back later.
            </p>
          </div>
        )}
    </div>
  );

  function getQualityBadgeStyle(quality: string) {
    switch (quality) {
      case "2160p":
        return {
          background: "rgba(139, 92, 246, 0.2)",
          color: "#a78bfa",
          border: "rgba(139, 92, 246, 0.3)",
        };
      case "1080p":
        return {
          background: "rgba(59, 130, 246, 0.2)",
          color: "#93c5fd",
          border: "rgba(59, 130, 246, 0.3)",
        };
      case "720p":
        return {
          background: "rgba(34, 197, 94, 0.2)",
          color: "#4ade80",
          border: "rgba(34, 197, 94, 0.3)",
        };
      default:
        return {
          background: "rgba(107, 114, 128, 0.2)",
          color: "#9ca3af",
          border: "rgba(107, 114, 128, 0.3)",
        };
    }
  }
};
