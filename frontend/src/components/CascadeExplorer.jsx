/**
 * NeerNetra -- CascadeExplorer
 * ==============================
 * What-if tool for the landslide -> blockage -> flood-amplification
 * chain (GET /api/cascade). Unlike the cascade embedded in the live
 * risk map (which uses current weather), this lets you type in
 * arbitrary rainfall to test scenarios.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { dynamicsAPI } from '../services/api';
import { riskColor } from '../utils/constants';

function ChainStage({ title, data, extra }) {
  const color = riskColor(data.level);
  return (
    <div className="chain-stage">
      <div className="chain-stage-head">
        <span className="chain-stage-title">{title}</span>
        <span className="chain-stage-level" style={{ color, borderColor: color }}>{data.level}</span>
      </div>
      <div className="chain-stage-bar">
        <div className="chain-stage-fill" style={{ width: `${data.score * 100}%`, background: color }} />
      </div>
      {extra}
      {(data.triggers || data.factors || []).map((t, i) => (
        <p key={i} className="chain-reason">&bull; {t}</p>
      ))}
    </div>
  );
}

function CascadeExplorer({ locations }) {
  const [location, setLocation] = useState(locations?.[0]?.name || '');
  const [rain6h, setRain6h] = useState(40);
  const [rain24h, setRain24h] = useState(90);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const debounceRef = useRef(null);

  useEffect(() => {
    if (!location && locations?.length) setLocation(locations[0].name);
  }, [locations, location]);

  const run = useCallback(() => {
    if (!location) return;
    setLoading(true);
    dynamicsAPI.getCascade(location, rain6h, rain24h)
      .then((res) => setResult(res.data))
      .catch(() => setResult(null))
      .finally(() => setLoading(false));
  }, [location, rain6h, rain24h]);

  useEffect(() => {
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(run, 250);
    return () => clearTimeout(debounceRef.current);
  }, [run]);

  return (
    <div className="panel-card explorer-tool">
      <h3>Cascade what-if</h3>
      <p className="tool-desc">
        Landslide-blockage-flood chain for any location. Move the rainfall sliders to
        test scenarios beyond current weather.
      </p>

      <label className="field-label">
        Location
        <select className="select-input" value={location} onChange={(e) => setLocation(e.target.value)}>
          {(locations || []).map((l) => <option key={l.name} value={l.name}>{l.name}</option>)}
        </select>
      </label>

      <label className="field-label">
        6h rainfall: <span className="field-value">{rain6h} mm</span>
        <input type="range" min={0} max={200} value={rain6h} onChange={(e) => setRain6h(Number(e.target.value))} className="range-input" />
      </label>
      <label className="field-label">
        24h rainfall: <span className="field-value">{rain24h} mm</span>
        <input type="range" min={0} max={350} value={rain24h} onChange={(e) => setRain24h(Number(e.target.value))} className="range-input" />
      </label>

      {result && (
        <div className="cascade-result" style={{ opacity: loading ? 0.6 : 1 }}>
          <div className="cascade-overall">
            <span>Overall cascade risk</span>
            <span className="risk-level-badge" style={{ borderColor: riskColor(result.cascade_risk_level), color: riskColor(result.cascade_risk_level) }}>
              {result.cascade_risk_level}
            </span>
          </div>

          <ChainStage title="1. Landslide risk" data={result.chain.landslide_risk} />
          <ChainStage title="2. River blockage" data={result.chain.blockage_risk} />
          <ChainStage
            title="3. Downstream amplification"
            data={result.chain.flood_amplification}
            extra={
              result.chain.flood_amplification.downstream_risk_increase_pct > 0 && (
                <p className="chain-reason">
                  &bull; Downstream risk +{result.chain.flood_amplification.downstream_risk_increase_pct}%
                </p>
              )
            }
          />

          <p className="disclaimer-text">{result.disclaimer}</p>
        </div>
      )}
    </div>
  );
}

export default CascadeExplorer;
