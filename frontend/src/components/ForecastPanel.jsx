/**
 * NeerNetra -- ForecastPanel
 * ============================
 * Hourly rainfall forecast for the selected location, bucketed into
 * 3-hour bars so 24/48/72h windows all stay legible without a
 * charting library.
 */

import { useState, useEffect, useCallback } from 'react';
import { weatherAPI } from '../services/api';

const HOUR_OPTIONS = [24, 48, 72];

function bucketHourly(hourly) {
  const buckets = [];
  for (let i = 0; i < hourly.length; i += 3) {
    const slice = hourly.slice(i, i + 3);
    if (slice.length === 0) continue;
    const rain = slice.reduce((sum, h) => sum + (h.precipitation || 0), 0);
    const temp = slice.reduce((sum, h) => sum + (h.temperature_2m || 0), 0) / slice.length;
    buckets.push({ time: slice[0].time, rain: Math.round(rain * 10) / 10, temp: Math.round(temp) });
  }
  return buckets;
}

function ForecastPanel({ lat, lon, label }) {
  const [hours, setHours] = useState(48);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  const load = useCallback(() => {
    if (lat == null || lon == null) return;
    setLoading(true);
    setError(false);
    weatherAPI.getForecast(lat, lon, hours)
      .then((res) => setData(res.data))
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [lat, lon, hours]);

  useEffect(() => { load(); }, [load]);

  if (lat == null || lon == null) {
    return (
      <div className="panel-card">
        <h3>Hourly forecast</h3>
        <p className="stub-text">Select a location to see its forecast.</p>
      </div>
    );
  }

  const buckets = data ? bucketHourly(data.hourly || []) : [];
  const maxRain = Math.max(1, ...buckets.map((b) => b.rain));

  return (
    <div className="panel-card">
      <div className="risk-header">
        <h3>Hourly forecast</h3>
        <div className="forecast-hour-toggle">
          {HOUR_OPTIONS.map((h) => (
            <button
              key={h}
              type="button"
              className={`toggle-chip${hours === h ? ' toggle-chip-active' : ''}`}
              onClick={() => setHours(h)}
            >
              {h}h
            </button>
          ))}
        </div>
      </div>

      {label && <p className="forecast-loc-label">{label}</p>}

      {loading && !data && <div className="loading-pulse">Loading forecast...</div>}
      {error && <p className="stub-text">Forecast unavailable right now.</p>}

      {data && (
        <>
          {data.elevation_m != null && (
            <div className="weather-row">
              <span className="weather-item">{Math.round(data.elevation_m)} m elevation</span>
              {data.current?.temperature_2m != null && (
                <span className="weather-item">{data.current.temperature_2m}&deg;C now</span>
              )}
            </div>
          )}

          <div className="forecast-chart" style={{ opacity: loading ? 0.5 : 1 }}>
            {buckets.map((b, i) => {
              const pct = Math.max(2, (b.rain / maxRain) * 100);
              const dt = new Date(b.time);
              return (
                <div key={i} className="forecast-bar-col">
                  <span className="forecast-bar-val">{b.rain > 0 ? b.rain : ''}</span>
                  <div className="forecast-bar-track">
                    <div className="forecast-bar-fill" style={{ height: `${pct}%` }} />
                  </div>
                  <span className="forecast-bar-time">
                    {dt.toLocaleTimeString([], { hour: 'numeric' })}
                  </span>
                </div>
              );
            })}
          </div>
          <p className="disclaimer-text">3-hour buckets, mm of rain. Source: Open-Meteo.</p>
        </>
      )}
    </div>
  );
}

export default ForecastPanel;
