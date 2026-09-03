/**
 * NeerNetra -- NavBar
 * =====================
 * Persistent top bar: brand, section nav, and a live backend status
 * pill driven by GET /health.
 */

import { useState, useEffect, useCallback } from 'react';
import { NavLink } from 'react-router-dom';
import { systemAPI } from '../services/api';

const NAV_ITEMS = [
  { to: '/', label: 'Live Map', end: true },
  { to: '/explorer', label: 'Explorer' },
  { to: '/locations', label: 'Locations' },
  { to: '/history', label: 'History' },
  { to: '/demo', label: 'Demo Replay' },
];

function NavBar() {
  const [health, setHealth] = useState({ status: 'checking' });

  const ping = useCallback(async () => {
    try {
      const res = await systemAPI.healthCheck();
      setHealth({ status: 'online', data: res.data });
    } catch {
      setHealth({ status: 'offline' });
    }
  }, []);

  useEffect(() => {
    ping();
    const interval = setInterval(ping, 60 * 1000);
    return () => clearInterval(interval);
  }, [ping]);

  return (
    <header className="navbar">
      <div className="navbar-brand">
        <svg className="brand-mark" viewBox="0 0 48 48" aria-hidden="true">
          <path d="M4 30 Q14 24 24 30 T44 30" fill="none" stroke="#274038" strokeWidth="2" />
          <path d="M2 22 Q14 15 24 22 T46 22" fill="none" stroke="#31504A" strokeWidth="2" />
          <path
            d="M24 6 C19 16 30 20 22 30 C17 36 24 42 24 42"
            fill="none" stroke="#3FBFAD" strokeWidth="3.4" strokeLinecap="round"
          />
        </svg>
        <div className="brand-text">
          <span className="brand-name">NeerNetra</span>
          <span className="brand-caption">Mandakini Valley flood watch</span>
        </div>
      </div>

      <nav className="navbar-nav">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) => `nav-link${isActive ? ' nav-link-active' : ''}`}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="navbar-status" title={health.data ? `v${health.data.version}` : ''}>
        <span className={`status-dot status-dot-${health.status}`} />
        <span className="status-text">
          {health.status === 'online' ? 'Backend live' : health.status === 'offline' ? 'Backend unreachable' : 'Connecting'}
        </span>
      </div>
    </header>
  );
}

export default NavBar;
