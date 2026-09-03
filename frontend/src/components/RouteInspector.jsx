/**
 * NeerNetra -- RouteInspector
 * =============================
 * Point-to-point tool: pick an origin and a target, get the specific
 * arrival-time estimate and evacuation window for that pair, at a
 * chosen scenario probability and rainfall intensity.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { dynamicsAPI } from '../services/api';
import {
  urgencyColor, URGENCY_LABELS, formatMinutes, formatPct, riskColor,
} from '../utils/constants';

function RouteInspector({ locations }) {
  const names = (locations || []).map((l) => l.name);
  const [origin, setOrigin] = useState(names[0] || '');
  const [target, setTarget] = useState(names[2] || names[names.length - 1] || '');
  const [probability, setProbability] = useState(0.8);
  const [intensity, setIntensity] = useState(1.5);
  const [arrival, setArrival] = useState(null);
  const [lset, setLset] = useState(null);
  const [loading, setLoading] = useState(false);
  const debounceRef = useRef(null);

  useEffect(() => {
    if (!origin && names.length) setOrigin(names[0]);
    if (!target && names.length > 1) setTarget(names[1]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [names.length]);

  const run = useCallback(() => {
    if (!origin || !target || origin === target) {
      setArrival(null); setLset(null);
      return;
    }
    setLoading(true);
    Promise.all([
      dynamicsAPI.getArrivalTime(origin, target, probability, intensity),
      dynamicsAPI.getLSET(origin, target, probability, intensity),
    ])
      .then(([a, l]) => { setArrival(a.data); setLset(l.data); })
      .catch(() => { setArrival(null); setLset(null); })
      .finally(() => setLoading(false));
  }, [origin, target, probability, intensity]);

  useEffect(() => {
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(run, 250);
    return () => clearTimeout(debounceRef.current);
  }, [run]);

  return (
    <div className="panel-card explorer-tool">
      <h3>Route inspector</h3>
      <p className="tool-desc">Arrival time and evacuation window for a specific origin-target pair.</p>

      <div className="route-selects">
        <label className="field-label">
          Origin
          <select className="select-input" value={origin} onChange={(e) => setOrigin(e.target.value)}>
            {names.map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
        </label>
        <label className="field-label">
          Target
          <select className="select-input" value={target} onChange={(e) => setTarget(e.target.value)}>
            {names.map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
        </label>
      </div>

      <label className="field-label">
        Origin probability: <span className="field-value">{formatPct(probability)}</span>
        <input type="range" min={0.1} max={1} step={0.05} value={probability} onChange={(e) => setProbability(Number(e.target.value))} className="range-input" />
      </label>
      <label className="field-label">
        Rainfall intensity: <span className="field-value">{intensity.toFixed(1)}x</span>
        <input type="range" min={0.5} max={3} step={0.1} value={intensity} onChange={(e) => setIntensity(Number(e.target.value))} className="range-input" />
      </label>

      {origin === target && <p className="stub-text">Pick two different locations.</p>}

      {arrival && origin !== target && (
        <div className="route-result" style={{ opacity: loading ? 0.6 : 1 }}>
          {arrival.estimated_arrival_time ? (
            <>
              <div className="route-result-row">
                <span>Travel time</span>
                <span className="route-result-val">{formatMinutes(arrival.travel_time_minutes)}</span>
              </div>
              <div className="route-result-row">
                <span>Distance</span>
                <span className="route-result-val">{arrival.distance_from_origin_km} km</span>
              </div>
              <div className="route-result-row">
                <span>Propagation speed</span>
                <span className="route-result-val">{arrival.propagation_speed_kmh} km/h</span>
              </div>
              <div className="route-result-row">
                <span>Risk at target</span>
                <span className="route-result-val" style={{ color: riskColor(arrival.risk_level_at_target) }}>
                  {arrival.risk_level_at_target} ({formatPct(arrival.flood_probability_at_target)})
                </span>
              </div>
              <div className="route-result-row">
                <span>Estimate confidence</span>
                <span className="route-result-val">{arrival.confidence}</span>
              </div>

              {lset?.lset && (
                <div className="route-lset-callout" style={{ borderColor: urgencyColor(lset.urgency) }}>
                  <span style={{ color: urgencyColor(lset.urgency) }}>
                    {URGENCY_LABELS[lset.urgency] || lset.urgency}
                  </span>
                  <span>
                    Last safe evacuation window: {formatMinutes(lset.time_until_lset_minutes)}
                    {' '}(buffer {lset.safety_buffer_minutes}min)
                  </span>
                </div>
              )}
              <p className="disclaimer-text">{arrival.disclaimer}</p>
            </>
          ) : (
            <p className="stub-text">{arrival.message}</p>
          )}
        </div>
      )}
    </div>
  );
}

export default RouteInspector;
