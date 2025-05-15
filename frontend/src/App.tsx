import React from "react";
import { Route, BrowserRouter as Router, Routes } from "react-router-dom";
import LogsList from "./components/LogsList";
import SeriesList from "./components/SeriesList";
import SeriesPage from "./components/SeriesPage";
import TasksPage from "./components/TasksPage";

const App: React.FC = () => {
  return (
    <div>
      <header className="bg-gray-800">
        <div className="container mx-auto px-4 py-4">
          <nav className="mt-2">
            <ul className="flex space-x-6">
              <li>
                <a
                  href="/"
                  className="text-white px-3 py-2 rounded hover:bg-gray-700 hover:text-gray-300"
                >
                  Home
                </a>
              </li>
              <li>
                <a
                  href="/logs"
                  className="text-white px-3 py-2 rounded hover:bg-gray-700 hover:text-gray-300"
                >
                  Logs
                </a>
              </li>
              <li>
                <a
                  href="/tasks"
                  className="text-white px-3 py-2 rounded hover:bg-gray-700 hover:text-gray-300"
                >
                  Tasks
                </a>
              </li>
            </ul>
          </nav>
        </div>
      </header>
      <Router>
        <div className="bg-gray-900 text-white min-h-screen flex">
          <div className="container mx-auto mt-10">
            <Routes>
              <Route path="/" element={<SeriesList />} />
              <Route path="/show/:showId" element={<SeriesPage />} />
              <Route path="/logs" element={<LogsList />} />
              <Route path="/tasks" element={<TasksPage />} />
            </Routes>
          </div>
        </div>
      </Router>
    </div>
  );
};

export default App;
