import {
  Link,
  Route,
  BrowserRouter as Router,
  Routes,
  useLocation,
} from "react-router-dom";
import { RequestPage } from "./components/RequestPage";
import { RequestsList } from "./components/RequestsList";

function Navigation() {
  const location = useLocation();

  return (
    <nav className="nav">
      <div className="nav-container">
        <Link to="/" className="nav-brand">
          Releasarr
        </Link>
        <ul className="nav-links">
          <li>
            <Link
              to="/"
              className={`nav-link ${
                location.pathname === "/" ? "active" : ""
              }`}
            >
              Requests
            </Link>
          </li>
        </ul>
      </div>
    </nav>
  );
}

function App() {
  return (
    <div className="app">
      <Router>
        <Navigation />

        <main className="main-content">
          <Routes>
            <Route path="/" element={<RequestsList />} />
            <Route path="/request/:id" element={<RequestPage />} />
          </Routes>
        </main>
      </Router>
    </div>
  );
}

export default App;
