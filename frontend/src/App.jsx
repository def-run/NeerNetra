/**
 * NeerNetra -- App Entry
 * =======================
 * Flash Flood Risk Prediction System
 */

import { BrowserRouter, Routes, Route } from 'react-router-dom';
import TopBar from './components/TopBar';
import Sidebar from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import Explorer from './pages/Explorer';
import Locations from './pages/Locations';
import History from './pages/History';
import DemoReplay from './pages/DemoReplay';
import './App.css';

function App() {
  return (
    <BrowserRouter>
      <div className="app-shell">
        <TopBar />
        <div className="app-body">
          <Sidebar />
          <main className="app-main">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/explorer" element={<Explorer />} />
              <Route path="/locations" element={<Locations />} />
              <Route path="/history" element={<History />} />
              <Route path="/demo" element={<DemoReplay />} />
            </Routes>
          </main>
        </div>
      </div>
    </BrowserRouter>
  );
}

export default App;
