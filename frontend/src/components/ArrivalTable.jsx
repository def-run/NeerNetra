/**
 * NeerNetra -- ArrivalTable
 * ===========================
 * Table view of estimated arrival time at every downstream location
 * for the current scenario. Complements the animated PropagationSlider.
 */

import { useState, useEffect } from 'react';
import { dynamicsAPI } from '../services/api';
import { CONFIDENCE_COLORS, formatMinutes, formatPct } from '../utils/constants';

function ArrivalTable({ origin, probability, rainfallIntensity }) {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!origin) return;
    setLoading(true);
    dynamicsAPI.getAllArrivals(origin, probability || 0.8, rainfallIntensity || 1.0)
      .then((res) => setRows(res.data.downstream_arrivals || []))
      .catch(() => setRows([]))
      .finally(() => setLoading(false));
  }, [origin, probability, rainfallIntensity]);

  return (
    <div className="panel-card">
      <h3>Downstream arrival times</h3>
      {loading && rows.length === 0 && <div className="loading-pulse">Computing arrivals...</div>}
      {!loading && rows.length === 0 && <p className="stub-text">Choose a flood origin above.</p>}

      {rows.length > 0 && (
        <div className="arrival-table" style={{ opacity: loading ? 0.6 : 1 }}>
          <div className="arrival-table-head">
            <span>Location</span>
            <span>ETA</span>
            <span>Dist.</span>
            <span>Probability</span>
          </div>
          {rows.map((r, i) => (
            <div key={i} className="arrival-table-row">
              <span className="arrival-loc">{r.location}</span>
              <span>{formatMinutes(r.time_remaining_minutes)}</span>
              <span>{r.distance_km} km</span>
              <span style={{ color: CONFIDENCE_COLORS[r.confidence] || 'inherit' }}>
                {r.flood_probability != null ? formatPct(r.flood_probability) : '--'}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default ArrivalTable;
