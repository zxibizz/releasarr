import React, { useEffect, useState } from "react";

interface Show {
  id: string;
  tvdb_data: {
    title: string;
    year: number;
    image_url: string;
  };
  missing_seasons: number[];
}

const SeriesList: React.FC = () => {
  const [shows, setShows] = useState<Show[]>([]);

  useEffect(() => {
    const fetchShows = async () => {
      try {
        const apiUrl = process.env.REACT_APP_BACKEND_URL;
        const response = await fetch(`${apiUrl}/api/shows/?only_missing=1`);
        const data = await response.json();
        setShows(data);
      } catch (error) {
        console.error("Error fetching shows:", error);
      }
    };

    fetchShows();
  }, []);

  return (
    <div>
      <h1 className="text-3xl font-bold mb-5">Запросы</h1>
      {shows.map((show) => (
        <div key={show.id} className="bg-gray-800 rounded-lg p-5 mb-5 flex">
          <img
            src={show.tvdb_data.image_url}
            alt={show.tvdb_data.title}
            className="w-24 h-36 rounded-lg mr-5"
          />
          <div>
            <h5 className="text-2xl font-semibold mb-3">
              <a
                href={`/show/${show.id}`}
                className="text-blue-400 hover:underline"
              >
                {show.tvdb_data.title} ({show.tvdb_data.year})
              </a>
            </h5>
            <p className="mb-2">Сезоны</p>
            <div className="flex space-x-2">
              {show.missing_seasons.map((season) => (
                <span
                  key={season}
                  className="bg-gray-700 text-white py-1 px-3 rounded-full"
                >
                  {season}
                </span>
              ))}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

export default SeriesList;
