import React, { useState } from "react";
import { useRequests } from "../hooks/useRequests";
import { RequestCard } from "./RequestCard";

export const RequestsList: React.FC = () => {
  const { requests, loading, error, fetchByStatus, fetchByType, refetch } =
    useRequests();
  const [activeFilter, setActiveFilter] = useState<string>("all");

  const handleFilterChange = async (filter: string) => {
    setActiveFilter(filter);

    switch (filter) {
      case "all":
        await refetch();
        break;
      case "movies":
        await fetchByType("movie");
        break;
      case "series":
        await fetchByType("series");
        break;
      case "pending":
      case "searching":
      case "downloading":
      case "completed":
      case "failed":
        await fetchByStatus(filter);
        break;
      default:
        await refetch();
    }
  };

  const filterButtons = [
    { key: "all", label: "All" },
    { key: "movies", label: "Movies" },
    { key: "series", label: "Series" },
    { key: "pending", label: "Pending" },
    { key: "approved", label: "Approved" },
    { key: "completed", label: "Completed" },
    { key: "rejected", label: "Rejected" },
  ];

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner"></div>
        <span>Loading requests...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="error">
        <div>❌ Error loading requests</div>
        <p>{error}</p>
        <button onClick={refetch} className="btn btn-secondary">
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div className="fade-in">
      {/* Page Header */}
      <div className="page-header">
        <h1 className="page-title">Media Requests</h1>
        <p className="page-subtitle">
          Track and manage your media server requests
        </p>
      </div>

      {/* Filter Tabs */}
      <div className="filter-tabs">
        {filterButtons.map((filter) => (
          <button
            key={filter.key}
            onClick={() => handleFilterChange(filter.key)}
            className={`filter-tab ${
              activeFilter === filter.key ? "active" : ""
            }`}
          >
            {filter.label}
          </button>
        ))}
      </div>

      {/* Results Summary */}
      <div style={{ marginBottom: "1.5rem" }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <h2
            style={{ fontSize: "1.25rem", fontWeight: "600", color: "#f1f5f9" }}
          >
            {activeFilter === "all"
              ? "All Requests"
              : `${
                  filterButtons.find((f) => f.key === activeFilter)?.label
                } Requests`}
          </h2>
          <span style={{ color: "#94a3b8", fontSize: "0.875rem" }}>
            {requests.length} {requests.length === 1 ? "request" : "requests"}
          </span>
        </div>
      </div>

      {/* Requests Grid */}
      {requests.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">📺</div>
          <h3 className="empty-state-title">No requests found</h3>
          <p className="empty-state-description">
            {activeFilter === "all"
              ? "No media requests have been created yet."
              : `No requests match the "${activeFilter}" filter.`}
          </p>
        </div>
      ) : (
        <div className="card-grid">
          {requests.map((request) => (
            <RequestCard key={request.id} request={request} />
          ))}
        </div>
      )}
    </div>
  );
};
