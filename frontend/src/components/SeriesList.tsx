import React from 'react';

interface Show {
  id: string;
  tvdb_data: {
    title: string;
    year: number;
    image_url: string;
  };
  missing_seasons: number[];
}

// Mock Data to Represent API Response
const mockShows: Show[] = [
  {
    id: '1',
    tvdb_data: {
      title: 'Breaking Bad',
      year: 2008,
      image_url: 'https://via.placeholder.com/150',
    },
    missing_seasons: [1, 3],
  },
  {
    id: '2',
    tvdb_data: {
      title: 'Game of Thrones',
      year: 2011,
      image_url: 'https://via.placeholder.com/150',
    },
    missing_seasons: [4],
  },
];

const SeriesList: React.FC = () => {
  const shows = mockShows; // Replace this with API call when backend is ready

  return (
    <div>
      <h1 className="text-3xl font-bold mb-5">Запросы</h1>
      {shows.map((show) => (
        <div
          key={show.id}
          className="bg-gray-800 rounded-lg p-5 mb-5 flex"
        >
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