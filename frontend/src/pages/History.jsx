/**
 * NeerNetra -- History page
 * ===========================
 * Chronological timeline of historical flood events in the pilot
 * region, oldest first.
 */

import { useState, useEffect, useMemo } from 'react';
import EventCard from '../components/EventCard';
import { floodEventsAPI } from '../services/api';

function History() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    floodEventsAPI.getEvents()
      .then((res) => setData(res.data))
      .catch(() => setError(true));
  }, []);

  const sorted = useMemo(() => {
    if (!data?.events) return [];
    return [...data.events].sort((a, b) => new Date(a.event_date) - new Date(b.event_date));
  }, [data]);

  const deadliest = useMemo(() => {
    if (!sorted.length) return null;
    return sorted.reduce((max, e) => (e.deaths > (max?.deaths || 0) ? e : max), null);
  }, [sorted]);

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>Flood history</h1>
        <p>{data ? data.pilot_region : 'Loading historical events...'}</p>
      </div>

      {error && <p className="stub-text">Could not load historical events.</p>}

      {sorted.length > 0 && (
        <div className="history-stats">
          <div className="history-stat">
            <span className="history-stat-val">{sorted.length}</span>
            <span className="history-stat-label">Recorded events</span>
          </div>
          <div className="history-stat">
            <span className="history-stat-val">{sorted[sorted.length - 1].event_date.slice(0, 4)}</span>
            <span className="history-stat-label">Most recent</span>
          </div>
          {deadliest && (
            <div className="history-stat">
              <span className="history-stat-val">{deadliest.location_name}</span>
              <span className="history-stat-label">Deadliest ({deadliest.event_date.slice(0, 4)})</span>
            </div>
          )}
        </div>
      )}

      <div className="history-timeline">
        {sorted.map((ev) => <EventCard key={ev.id} event={ev} />)}
      </div>
    </div>
  );
}

export default History;
