/**
 * NeerNetra -- LSETPanel
 * ========================
 * Last Safe Evacuation Time for every location downstream of the
 * selected flood origin, sorted by urgency (most urgent first).
 */

import { useState, useEffect } from 'react';
import { dynamicsAPI } from '../services/api';
import { urgencyColor, URGENCY_LABELS, formatMinutes } from '../utils/constants';

function LSETPanel({ origin, probability, rainfallIntensity }) {
  const [lsetData, setLsetData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!origin) return;
    setLoading(true);
    dynamicsAPI.getAllLSET(origin, probability || 0.8, rainfallIntensity || 1.0)
      .then((res) => setLsetData(res.data))
      .catch((err) => console.error('LSET error:', err))
      .finally(() => setLoading(false));
  }, [origin, probability, rainfallIntensity]);

  const results = lsetData?.lset_results || [];

  return (
    <div className="panel-card">
      <h3>Evacuation timeline</h3>
      {loading && results.length === 0 && <div className="loading-pulse">Computing LSET...</div>}
      {!loading && results.length === 0 && (
        <p className="stub-text">Choose a flood origin above to see evacuation windows.</p>
      )}
      {results.length > 0 && (
        <div className="lset-list" style={{ opacity: loading ? 0.6 : 1 }}>
          {results.map((item, i) => {
            const urgency = item.urgency || 'MONITOR';
            const color = urgencyColor(urgency);
            return (
              <div key={i} className="lset-item" style={{ borderLeftColor: color }}>
                <div className="lset-location">
                  <span className="lset-name">{item.location}</span>
                  <span className="lset-urgency" style={{ color }}>{URGENCY_LABELS[urgency] || urgency}</span>
                </div>
                <div className="lset-times">
                  <span className="lset-remaining">
                    {item.time_until_lset_minutes > 0 ? formatMinutes(item.time_until_lset_minutes) : 'Expired'}
                  </span>
                  <span className="lset-buffer">buffer {item.safety_buffer_minutes}min</span>
                </div>
                {item.flood_probability != null && (
                  <div className="lset-prob-bar">
                    <div
                      className="lset-prob-fill"
                      style={{ width: `${Math.min(item.flood_probability * 100, 100)}%`, background: color }}
                    />
                  </div>
                )}
                {item.confidence && (
                  <span className="lset-confidence">confidence: {item.confidence.toLowerCase()}</span>
                )}
              </div>
            );
          })}
        </div>
      )}
      <p className="disclaimer-text">Planning estimate. Not a guarantee. Follow official evacuation orders.</p>
    </div>
  );
}

export default LSETPanel;
