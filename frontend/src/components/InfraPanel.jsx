/**
 * NeerNetra -- InfraPanel
 * =========================
 * Bridges and road segments exposed to the current flood scenario,
 * sorted by priority score.
 */

import { useState, useEffect } from 'react';
import { dynamicsAPI } from '../services/api';
import { riskColor } from '../utils/constants';

function AssetRow({ asset }) {
  const color = riskColor(asset.risk_level || 'LOW');
  return (
    <div className="infra-item">
      <div className="infra-item-main">
        <span className="infra-name">{asset.name}</span>
        <span className="infra-risk-badge" style={{ color, background: `${color}22` }}>{asset.risk_level}</span>
      </div>
      <div className="infra-item-meta">
        <span>{asset.distance_to_flood_km != null ? `${asset.distance_to_flood_km} km from flood` : ''}</span>
        {asset.time_remaining_minutes != null && <span>{asset.time_remaining_minutes} min remaining</span>}
        {asset.priority_score != null && <span>priority {asset.priority_score}</span>}
      </div>
    </div>
  );
}

function InfraPanel({ origin, probability, rainfallIntensity }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!origin) return;
    setLoading(true);
    dynamicsAPI.getInfrastructureRisk(origin, probability || 0.8, rainfallIntensity || 1.0)
      .then((res) => setData(res.data))
      .catch((err) => console.error('Infra error:', err))
      .finally(() => setLoading(false));
  }, [origin, probability, rainfallIntensity]);

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

  return (
    <div className="panel-card">
      <h3>Infrastructure exposure</h3>
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
