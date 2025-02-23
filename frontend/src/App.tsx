import React from 'react';
import { Route, BrowserRouter as Router, Routes } from 'react-router-dom';
import SeriesList from './components/SeriesList';
import SeriesPage from './components/SeriesPage';

const App: React.FC = () => {
  return (
    <Router>
      <div className="bg-gray-900 text-white min-h-screen flex">
        <div className="container mx-auto mt-10">
          <Routes>
            {/* Main page */}
            <Route path="/" element={<SeriesList />} />
            <Route path="/show/:showId" element={<SeriesPage />} />
          </Routes>
        </div>
      </div>
    </Router>
  );
};

export default App;
