/**
 * NeerNetra -- App Entry
 * =======================
 * Flash Flood Risk Prediction System
 */

import { BrowserRouter, Routes, Route } from 'react-router-dom';
import NavBar from './components/NavBar';
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
        <NavBar />
        <main className="app-main">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/explorer" element={<Explorer />} />
            <Route path="/locations" element={<Locations />} />
            <Route path="/history" element={<History />} />
            <Route path="/demo" element={<DemoReplay />} />
          </Routes>
        </main>
        <footer className="app-footer">
          <span>NeerNetra &mdash; Flash Flood Risk Prediction for the Kedarnath / Mandakini Valley</span>
          <span>Decision-support estimates only. Always follow official evacuation orders.</span>
        </footer>
      </div>
    </BrowserRouter>
  );
}

export default App;
