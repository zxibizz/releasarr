import React from "react";
import { Link } from "react-router-dom";
import { MediaRequest } from "../types";
import { formatDate, formatRuntime, getStatusIcon } from "../utils/formatters";

interface RequestCardProps {
  request: MediaRequest;
}

export const RequestCard: React.FC<RequestCardProps> = ({ request }) => {
  const isMovie = request.type === "movie";
  const statusIcon = getStatusIcon(request.status);

  return (
    <Link to={`/request/${request.id}`} className="request-card card">
      <div className="request-header">
        <div>
          <h3 className="request-title">{request.title}</h3>
          <p className="request-year">
            {request.year}
            {!isMovie && ` • Season ${request.season_number}`}
            {isMovie && ` • ${formatRuntime(request.runtime)}`}
          </p>
        </div>
        <div className={`status-badge ${request.status}`}>
          <span>{statusIcon}</span>
          <span>{request.status}</span>
        </div>
      </div>

      <div className="request-meta">
        <div className={`request-type ${request.type}`}>
          {request.type === "movie" ? "🎬" : "📺"} {request.type}
        </div>
        {request.genres.slice(0, 2).map((genre) => (
          <span
            key={genre}
            style={{
              padding: "0.25rem 0.5rem",
              background: "rgba(71, 85, 105, 0.5)",
              color: "#cbd5e1",
              fontSize: "0.75rem",
              borderRadius: "0.25rem",
            }}
          >
            {genre}
          </span>
        ))}
        {request.genres.length > 2 && (
          <span
            style={{
              padding: "0.25rem 0.5rem",
              background: "rgba(71, 85, 105, 0.5)",
              color: "#cbd5e1",
              fontSize: "0.75rem",
              borderRadius: "0.25rem",
            }}
          >
            +{request.genres.length - 2}
          </span>
        )}
      </div>

      <p className="request-description line-clamp-3">{request.overview}</p>

      {!isMovie && (
        <div
          style={{
            fontSize: "0.75rem",
            color: "#64748b",
            marginBottom: "0.5rem",
          }}
        >
          <span>{request.total_episodes} episodes</span>
          <span style={{ margin: "0 0.5rem" }}>•</span>
          <span>
            {request.series_title} ({request.series_year})
          </span>
        </div>
      )}

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          fontSize: "0.75rem",
          color: "#64748b",
          marginTop: "auto",
        }}
      >
        <span>Created {formatDate(request.created_at)}</span>
        <span style={{ textTransform: "capitalize" }}>{request.type}</span>
      </div>
    </Link>
  );
};
