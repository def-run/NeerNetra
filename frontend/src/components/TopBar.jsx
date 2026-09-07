/**
 * NeerNetra -- TopBar
 * =====================
 * Persistent top bar: brand, search, and notification/profile actions.
 * The profile icon carries a small live/offline status dot driven by
 * GET /health, so backend connectivity stays visible without taking
 * up header space.
 */

import { useState, useEffect, useCallback } from 'react';
import { systemAPI } from '../services/api';

function TopBar() {
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

  const statusTitle =
    health.status === 'online'
      ? `Backend live${health.data?.version ? ` \u00b7 v${health.data.version}` : ''}`
      : health.status === 'offline'
        ? 'Backend unreachable'
        : 'Connecting to backend...';

  return (
    <header className="topbar">
      <div className="topbar-brand">
        <img src="/favicon.svg" alt="Neer Netra" className="brand-mark" />
        <span className="topbar-brand-name">Neer Netra</span>
      </div>

      <div className="topbar-search">
        <svg viewBox="0 0 24 24" width="17" height="17" aria-hidden="true">
          <circle cx="11" cy="11" r="7" fill="none" stroke="currentColor" strokeWidth="2" />
          <line x1="16.2" y1="16.2" x2="21" y2="21" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </svg>
        <input type="text" placeholder="Search" aria-label="Search" />
      </div>

      <div className="topbar-actions">
        <button type="button" className="icon-btn" aria-label="Notifications" title="Notifications">
          <svg viewBox="0 0 24 24" width="19" height="19" aria-hidden="true">
            <path
              d="M6 17h12a2 2 0 0 1-2-2v-4a4 4 0 0 0-8 0v4a2 2 0 0 1-2 2Z"
              fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round"
            />
            <path d="M10 20a2 2 0 0 0 4 0" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
          </svg>
        </button>
        <button type="button" className="icon-btn icon-btn-profile" aria-label={statusTitle} title={statusTitle}>
          <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
            <circle cx="12" cy="8.5" r="3.5" fill="none" stroke="currentColor" strokeWidth="1.8" />
            <path d="M4.5 20a7.5 7.5 0 0 1 15 0" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
          </svg>
          <span className={`status-dot status-dot-${health.status}`} />
        </button>
      </div>
    </header>
  );
}

export default TopBar;
