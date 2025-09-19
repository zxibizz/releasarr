import React from "react";
import { MediaRequest } from "../types";
import { formatDate, formatRuntime, getStatusIcon } from "../utils/formatters";

interface MediaInfoProps {
  request: MediaRequest;
}

export const MediaInfo: React.FC<MediaInfoProps> = ({ request }) => {
  const isMovie = request.type === "movie";
  const statusIcon = getStatusIcon(request.status);

  return (
    <div className="card">
      <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
        {/* Header with Title and Status */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            flexWrap: "wrap",
            gap: "1rem",
          }}
        >
          <div>
            <h2
              style={{
                fontSize: "2rem",
                fontWeight: "700",
                color: "#f1f5f9",
                marginBottom: "0.5rem",
              }}
            >
              {request.title}
            </h2>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.5rem",
                color: "#94a3b8",
                fontSize: "1.125rem",
              }}
            >
              <span>{request.year}</span>
              {!isMovie && (
                <>
                  <span>•</span>
                  <span>Season {request.season_number}</span>
                </>
              )}
              {isMovie && (
                <>
                  <span>•</span>
                  <span>{formatRuntime(request.runtime)}</span>
                </>
              )}
            </div>
          </div>
          <div className={`status-badge ${request.status}`}>
            <span>{statusIcon}</span>
            <span>{request.status}</span>
          </div>
        </div>

        {/* Media Information Grid */}
        <div className="media-info">
          <div className="info-item">
            <div className="info-label">Type</div>
            <div className="info-value">
              {request.type === "movie" ? "🎬 Movie" : "📺 TV Series"}
            </div>
          </div>

          <div className="info-item">
            <div className="info-label">Created</div>
            <div className="info-value">{formatDate(request.created_at)}</div>
          </div>

          <div className="info-item">
            <div className="info-label">Updated</div>
            <div className="info-value">{formatDate(request.updated_at)}</div>
          </div>

          <div className="info-item">
            <div className="info-label">IMDb</div>
            <div className="info-value">
              <a
                href={`https://www.imdb.com/title/${request.imdb_id}`}
                target="_blank"
                rel="noopener noreferrer"
                style={{ color: "#3b82f6", textDecoration: "underline" }}
              >
                {request.imdb_id}
              </a>
            </div>
          </div>

          {!isMovie && (
            <>
              <div className="info-item">
                <div className="info-label">Series</div>
                <div className="info-value">
                  {request.series_title} ({request.series_year})
                </div>
              </div>
              <div className="info-item">
                <div className="info-label">Episodes</div>
                <div className="info-value">{request.total_episodes}</div>
              </div>
            </>
          )}
        </div>

        {/* Genres */}
        <div>
          <h3
            style={{
              fontSize: "1.125rem",
              fontWeight: "600",
              color: "#f1f5f9",
              marginBottom: "0.75rem",
            }}
          >
            Genres
          </h3>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
            {request.genres.map((genre) => (
              <span
                key={genre}
                style={{
                  padding: "0.375rem 0.75rem",
                  background: "rgba(71, 85, 105, 0.5)",
                  color: "#cbd5e1",
                  fontSize: "0.875rem",
                  borderRadius: "9999px",
                  border: "1px solid rgba(148, 163, 184, 0.2)",
                }}
              >
                {genre}
              </span>
            ))}
          </div>
        </div>

        {/* Overview */}
        <div>
          <h3
            style={{
              fontSize: "1.125rem",
              fontWeight: "600",
              color: "#f1f5f9",
              marginBottom: "0.75rem",
            }}
          >
            Overview
          </h3>
          <p
            style={{
              color: "#cbd5e1",
              lineHeight: "1.6",
              fontSize: "0.875rem",
            }}
          >
            {request.overview}
          </p>
        </div>
      </div>
    </div>
  );
};
