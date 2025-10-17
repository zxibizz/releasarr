import React from "react";
import { Link, useParams } from "react-router-dom";
import { useRequest } from "../hooks/useRequests";
import { MediaInfo } from "./MediaInfo";
import ReleasesList from "./ReleasesList";
import { TorrentSearch } from "./TorrentSearch";

export const RequestPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { request, loading, error } = useRequest(id || "");

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

          <ReleasesList requestId={request.id} />
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
    </div>
  );
};
