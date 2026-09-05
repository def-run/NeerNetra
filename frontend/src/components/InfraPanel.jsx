/**
 * NeerNetra -- InfraPanel
 * =========================
 * Bridges and road segments exposed to the current flood scenario,
 * sorted by priority score.
 *
 * Now uses real-time probability from the ML prediction. Shows a
 * "minimal exposure" state when risk is low. Includes withstand
 * assessment for each asset based on flood intensity.
 */

import { useState, useEffect } from 'react';
import { dynamicsAPI } from '../services/api';
import {
  riskColor, intensityColor, withstandColor,
  WITHSTAND_STATUSES, formatPct,
} from '../utils/constants';

function WithstandBadge({ withstand }) {
  if (!withstand) return null;
  const color = withstandColor(withstand.withstand_status);
  const label = WITHSTAND_STATUSES[withstand.withstand_status] || withstand.withstand_status;
  return (
    <span className="withstand-badge" style={{ color, background: `${color}18` }} title={withstand.explanation}>
      {label}
    </span>
  );
}

function AssetRow({ asset }) {
  const color = riskColor(asset.risk_level || 'LOW');
  return (
    <div className="infra-item">
      <div className="infra-item-main">
        <span className="infra-name">{asset.name}</span>
        <span className="infra-risk-badge" style={{ color, background: `${color}22` }}>{asset.risk_level}</span>
        <WithstandBadge withstand={asset.withstand} />
      </div>
      <div className="infra-item-meta">
        <span>{asset.distance_to_flood_km != null ? `${asset.distance_to_flood_km} km from flood` : ''}</span>
        {asset.time_remaining_minutes != null && <span>{asset.time_remaining_minutes} min remaining</span>}
        {asset.priority_score != null && <span>priority {asset.priority_score}</span>}
      </div>
      {asset.withstand?.explanation && (
        <div className="infra-item-withstand-note">{asset.withstand.explanation}</div>
      )}
    </div>
  );
}

function InfraPanel({ origin, probability, rainfallIntensity }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  const isLowRisk = probability < 0.25;

  useEffect(() => {
    if (!origin || isLowRisk) {
      setData(null);
      return;
    }
    setLoading(true);
    dynamicsAPI.getInfrastructureRisk(origin, probability, rainfallIntensity || 0.5)
      .then((res) => setData(res.data))
      .catch((err) => console.error('Infra error:', err))
      .finally(() => setLoading(false));
  }, [origin, probability, rainfallIntensity, isLowRisk]);

  if (isLowRisk) {
    return (
      <div className="panel-card">
        <h3>Infrastructure exposure</h3>
        <div className="low-risk-info">
          <span className="low-risk-icon">✓</span>
          <div>
            <p className="low-risk-title">Infrastructure exposure is minimal</p>
            <p className="low-risk-desc">
              Current flood probability is {formatPct(probability)} — risk level is LOW.
              Infrastructure assessment activates when flood probability exceeds 25%.
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (loading && !data) {
    return (
      <div className="panel-card">
        <h3>Infrastructure exposure</h3>
        <div className="loading-pulse">Analyzing exposure...</div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="panel-card">
        <h3>Infrastructure exposure</h3>
        <p className="stub-text">Choose a flood origin above.</p>
      </div>
    );
  }

  const bridges = data.exposed_bridges || [];
  const roads = data.exposed_roads || [];
  const intensity = data.flood_intensity;

  return (
    <div className="panel-card">
      <h3>Infrastructure exposure</h3>

      {/* Flood intensity summary */}
      {intensity && (
        <div className="infra-intensity-bar" style={{ borderColor: intensityColor(intensity.intensity_level) }}>
          <div className="infra-intensity-head">
            <span className="infra-intensity-label">Flood intensity</span>
            <span className="infra-intensity-level" style={{ color: intensityColor(intensity.intensity_level) }}>
              {intensity.intensity_level}
            </span>
          </div>
          {intensity.impact_summary && (
            <div className="infra-intensity-impacts">
              <span>Depth: {intensity.impact_summary.water_depth}</span>
              <span>Flow: {intensity.impact_summary.flow_velocity}</span>
            </div>
          )}
        </div>
      )}

      <div className="infra-summary">
        <div className="infra-stat">
          <span className="infra-count">{data.total_bridges_at_risk || 0}</span>
          <span className="infra-label">Bridges</span>
        </div>
        <div className="infra-stat">
          <span className="infra-count">{data.total_road_segments_at_risk || 0}</span>
          <span className="infra-label">Road segments</span>
        </div>
        <div className="infra-stat">
          <span className="infra-count">{data.critical_assets?.length || 0}</span>
          <span className="infra-label">Critical</span>
        </div>
      </div>

      {bridges.length > 0 && (
        <div className="infra-section">
          <h4>Bridges</h4>
          <div className="infra-scroll">
            {bridges.map((b, i) => <AssetRow key={i} asset={b} />)}
          </div>
        </div>
      )}

      {roads.length > 0 && (
        <div className="infra-section">
          <h4>Roads</h4>
          <div className="infra-scroll">
            {roads.map((r, i) => <AssetRow key={i} asset={r} />)}
          </div>
        </div>
      )}

      {bridges.length === 0 && roads.length === 0 && (
        <p className="stub-text">No infrastructure within the exposure radius of this scenario.</p>
      )}
    </div>
  );
}

export default InfraPanel;
