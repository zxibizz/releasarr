import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

interface Show {
  id: string;
  tvdb_data: {
    title: string;
    title_en: string;
    year: number;
    image_url: string;
    overview: string;
    country: string;
    genres: string[];
  };
  sonarr_data: {
    seasons: { season_number: number; total_episodes_count: number }[];
  };
  releases: any[]; // Define a more specific type if known
  prowlarr_data: any[]; // Define a more specific type if known
  prowlarr_search?: string;
}

const SeriesPage: React.FC = () => {
  const { showId } = useParams<{ showId: string }>();
  const [show, setShow] = useState<Show | null>(null);
  const [activeTab, setActiveTab] = useState("seasons");

  useEffect(() => {
    const fetchShow = async () => {
      try {
        const apiUrl = process.env.REACT_APP_BACKEND_URL;
        const response = await fetch(`${apiUrl}/api/shows/${showId}`);
        const data = await response.json();
        setShow(data);
      } catch (error) {
        console.error("Error fetching show:", error);
      }
    };

    fetchShow();
  }, [showId]);

  const handleTabClick = (tab: string) => {
    setActiveTab(tab);
  };

  if (!show) {
    return <div>Loading...</div>;
  }

  return (
    <div>
      <div className="flex space-x-5 mb-5">
        <img
          src={show.tvdb_data.image_url}
          alt={show.tvdb_data.title}
          className="w-48 h-72 rounded-lg"
        />
        <div>
          <h1 className="text-4xl font-bold mb-2">
            {show.tvdb_data.title} ({show.tvdb_data.year})
          </h1>
          <h2 className="text-2xl font-semibold mb-4">
            {show.tvdb_data.title_en}
          </h2>
          <p className="mb-3">{show.tvdb_data.overview}</p>
          <p className="mb-2">
            <strong>Country:</strong> {show.tvdb_data.country}
          </p>
          <p className="mb-2">
            <strong>Genres:</strong> {show.tvdb_data.genres.join(", ")}
          </p>
        </div>
      </div>

      <ul className="flex border-b">
        <li className="-mb-px mr-1">
          <a
            href="#seasons"
            className={`bg-gray-800 inline-block py-2 px-4 text-white font-semibold ${
              activeTab === "seasons" ? "border-b-2 border-blue-500" : ""
            }`}
            onClick={() => handleTabClick("seasons")}
          >
            Сезоны
          </a>
        </li>
        <li className="mr-1">
          <a
            href="#releases"
            className={`bg-gray-800 inline-block py-2 px-4 text-white font-semibold ${
              activeTab === "releases" ? "border-b-2 border-blue-500" : ""
            }`}
            onClick={() => handleTabClick("releases")}
          >
            Релизы
          </a>
        </li>
        <li className="mr-1">
          <a
            href="#search"
            className={`bg-gray-800 inline-block py-2 px-4 text-white font-semibold ${
              activeTab === "search" ? "border-b-2 border-blue-500" : ""
            }`}
            onClick={() => handleTabClick("search")}
          >
            Поиск
          </a>
        </li>
      </ul>

      <div
        id="seasons"
        className={`pt-5 ${activeTab === "seasons" ? "" : "hidden"}`}
      >
        <h3 className="text-2xl font-semibold mb-4">Сезоны</h3>
        <div className="space-y-3">
          {show.sonarr_data.seasons.map((season) => (
            <div
              key={season.season_number}
              className="bg-gray-800 rounded-lg p-4"
            >
              <p className="text-lg font-semibold">
                Season {season.season_number}
              </p>
              <p className="text-gray-400">
                {season.total_episodes_count} episodes
              </p>
            </div>
          ))}
        </div>
      </div>

      <div
        id="releases"
        className={`pt-5 ${activeTab === "releases" ? "" : "hidden"}`}
      >
        <h3 className="text-2xl font-semibold mb-4">Релизы</h3>
        {show.releases.map((release) => (
          <div key={release.name} className="bg-gray-800 rounded-lg p-5 mb-5">
            <h4 className="text-xl font-bold mb-3">{release.name}</h4>
            <p className="text-gray-400 mb-3">
              <strong>Updated At:</strong> {release.updated_at}
            </p>
            <p className="text-gray-400 mb-5">
              <strong>Search Term:</strong> {release.search}
            </p>
            {/* Form for file matching and delete actions */}
          </div>
        ))}
      </div>

      <div
        id="search"
        className={`pt-5 ${activeTab === "search" ? "" : "hidden"}`}
      >
        <h3 className="text-2xl font-semibold mb-4">Поиск</h3>
        <form action={`/show/${show.id}/search`} method="post" className="mb-5">
          <input
            type="text"
            name="query"
            className="bg-gray-700 text-white p-2 rounded-lg w-full"
            placeholder="Search..."
            value={show.prowlarr_search || show.tvdb_data.title}
          />
          <button
            type="submit"
            className="bg-blue-500 text-white py-2 px-4 rounded-lg mt-2"
          >
            Search
          </button>
        </form>
        {/* Search results will be displayed here */}
      </div>
    </div>
  );
};

export default SeriesPage;
