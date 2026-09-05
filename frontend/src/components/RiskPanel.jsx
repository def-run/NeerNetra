/**
 * NeerNetra -- RiskPanel
 * ========================
 * Flood risk assessment for the selected location: probability gauge,
 * risk level, confidence, driving factors, and flood intensity badge.
 */

import { riskColor, intensityColor, formatPct } from '../utils/constants';

function RiskPanel({ riskData, loading }) {
  if (loading && !riskData) {
    return (
      <div className="panel-card">
        <h3>Risk assessment</h3>
        <div className="loading-pulse">Fetching live data...</div>
      </div>
    );
  }

  if (!riskData) {
    return (
      <div className="panel-card">
        <h3>Risk assessment</h3>
        <p className="stub-text">Select a location on the map to see its risk assessment.</p>
      </div>
    );
  }

  const level = riskData.risk_level || 'LOW';
  const prob = riskData.risk_probability || 0;
  const color = riskColor(level);
  const conf = riskData.confidence || {};
  const drivers = riskData.drivers || [];
  const cascade = riskData.cascade;
  const intensity = riskData.flood_intensity;
  const station = riskData.location?.nearest_station || riskData.location?.name || 'Unknown';

  return (
    <div className="panel-card">
      <div className="risk-header">
        <h3>Flood risk</h3>
        <span className="location-tag">{station}</span>
      </div>

      <div className="risk-gauge">
        <div className="gauge-fill" style={{ width: `${Math.min(prob * 100, 100)}%`, background: color }} />
      </div>
      <div className="risk-gauge-row">
        <span className="risk-level-badge" style={{ borderColor: color, color }}>{level}</span>
        <span className="gauge-label">{formatPct(prob, 1)}</span>
      </div>

      {/* Flood intensity section */}
      {intensity && (
        <div className="intensity-section">
          <div className="intensity-row">
            <span className="intensity-label">Flood intensity</span>
            <span
              className="intensity-badge"
              style={{
                color: intensityColor(intensity.intensity_level),
                borderColor: intensityColor(intensity.intensity_level),
              }}
            >
              {intensity.intensity_level}
            </span>
            <span className="intensity-score">{formatPct(intensity.intensity_score, 0)}</span>
          </div>
          {intensity.description && (
            <p className="intensity-desc">{intensity.description}</p>
          )}
          {intensity.impact_summary && (
            <div className="intensity-impacts">
              <span>Depth: {intensity.impact_summary.water_depth}</span>
              <span>Flow: {intensity.impact_summary.flow_velocity}</span>
              {intensity.impact_summary.evacuation_needed && (
                <span className="intensity-evac-flag">⚠ Evacuation recommended</span>
              )}
            </div>
          )}
        </div>
      )}

      <div className="confidence-row">
        <span className="conf-label">Confidence</span>
        <span className={`conf-value conf-${(conf.confidence_level || '').toLowerCase()}`}>
          {conf.confidence_level || 'N/A'} ({formatPct(conf.confidence_score)})
        </span>
      </div>
      {conf.recommendation && <p className="conf-recommendation">{conf.recommendation}</p>}

      {cascade && (
        <div className="risk-cascade-inline">
          <span>Landslide-blockage cascade</span>
          <span className="risk-level-badge risk-level-badge-sm" style={{ borderColor: riskColor(cascade.cascade_risk_level), color: riskColor(cascade.cascade_risk_level) }}>
            {cascade.cascade_risk_level}
          </span>
        </div>
      )}

      {drivers.length > 0 && (
        <div className="drivers-section">
          <h4>Top drivers</h4>
          {drivers.map((d, i) => (
            <div key={i} className="driver-item">
              <span className="driver-factor">{d.factor}</span>
              <span className="driver-value">{d.value}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default RiskPanel;
