/**
 * NeerNetra -- LocationCard
 * ===========================
 * Directory card for one pilot location, with an inline "check
 * current rainfall" action (a lighter call than the full ML risk
 * assessment used on the Live Map).
 */

import { useState } from 'react';
import { weatherAPI } from '../services/api';
import { formatMm } from '../utils/constants';

function susceptibilityLabel(v) {
  if (v == null) return '--';
  if (v >= 0.7) return 'High';
  if (v >= 0.4) return 'Moderate';
  return 'Low';
}

function LocationCard({ location }) {
  const [rain, setRain] = useState(null);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);

  const check = () => {
    setOpen(true);
    if (rain) return;
    setLoading(true);
    weatherAPI.getRainfall(location.lat, location.lon)
      .then((res) => setRain(res.data))
      .catch(() => setRain({ error: true }))
      .finally(() => setLoading(false));
  };

  return (
    <div className="location-card">
      <h4>{location.name}</h4>
      <div className="location-stats">
        <div className="location-stat">
          <span className="location-stat-val">{location.elevation != null ? `${Math.round(location.elevation)}m` : '--'}</span>
          <span className="location-stat-label">Elevation</span>
        </div>
        <div className="location-stat">
          <span className="location-stat-val">{susceptibilityLabel(location.landslide_susceptibility)}</span>
          <span className="location-stat-label">Landslide risk</span>
        </div>
        <div className="location-stat">
          <span className="location-stat-val">{location.historical_flood_frequency ?? '--'}</span>
          <span className="location-stat-label">Past floods</span>
        </div>
      </div>
      <span className="location-coords">{location.lat?.toFixed(4)}, {location.lon?.toFixed(4)}</span>

      <button type="button" className="loc-check-btn" onClick={check}>
        {open ? 'Rainfall now' : 'Check rainfall now'}
      </button>

      {open && (
        <div className="loc-rain-result">
          {loading && <span className="loading-pulse">Checking...</span>}
          {rain?.error && <span className="stub-text">Unavailable right now.</span>}
          {rain && !rain.error && (
            <>
              <span>1h: {formatMm(rain.rainfall_features?.rain_1h)}</span>
              <span>24h: {formatMm(rain.rainfall_features?.rain_24h)}</span>
              <span>72h: {formatMm(rain.rainfall_features?.rain_72h)}</span>
            </>
          )}
        </div>
      )}
    </div>
  );
}

export default LocationCard;
