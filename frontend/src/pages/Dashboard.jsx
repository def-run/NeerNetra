/**
 * NeerNetra -- Dashboard (Live Map)
 * ===================================
 * The main operational view: live risk map for the 9 pilot locations,
 * click-anywhere risk querying, and a tabbed intel panel.
 *
 * LSET, Infrastructure, and Downstream tabs now use the **real-time
 * ML-predicted probability** from the selected location rather than
 * a hardcoded scenario value. Scenario simulation controls have been
 * moved to the Demo page.
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import FloodMap from '../maps/FloodMap';
import RiskPanel from '../components/RiskPanel';
import RainfallCard from '../components/RainfallCard';
import ForecastPanel from '../components/ForecastPanel';
import LSETPanel from '../components/LSETPanel';
import InfraPanel from '../components/InfraPanel';
import ArrivalTable from '../components/ArrivalTable';
import Tabs from '../components/Tabs';
import { riskAPI, dynamicsAPI, floodEventsAPI } from '../services/api';
import { formatClock } from '../utils/constants';

const TABS = [
  { id: 'risk', label: 'Risk' },
  { id: 'weather', label: 'Weather' },
  { id: 'evac', label: 'Evacuation' },
  { id: 'infra', label: 'Infrastructure' },
  { id: 'downstream', label: 'Downstream' },
];

const REFRESH_MS = 5 * 60 * 1000;

function Dashboard() {
  const [riskLocations, setRiskLocations] = useState([]);
  const [mapStatus, setMapStatus] = useState('loading');
  const [lastUpdated, setLastUpdated] = useState(null);
  const [selectedName, setSelectedName] = useState(null);

  const [propagation, setPropagation] = useState(null);

  const [activeTab, setActiveTab] = useState('risk');

  const [queryPoint, setQueryPoint] = useState(null);
  const [showHistory, setShowHistory] = useState(false);
  const [historicalEvents, setHistoricalEvents] = useState([]);

  const loadRiskMap = useCallback(() => {
    setMapStatus((s) => (s === 'loading' ? 'loading' : 'refreshing'));
    riskAPI.getRiskMap()
      .then((res) => {
        setRiskLocations(res.data.locations || []);
        setLastUpdated(res.data.updated_at);
        setMapStatus('ok');
      })
      .catch(() => setMapStatus('error'));
  }, []);

  useEffect(() => {
    loadRiskMap();
    const interval = setInterval(loadRiskMap, REFRESH_MS);
    return () => clearInterval(interval);
  }, [loadRiskMap]);

  const toggleHistory = () => {
    const next = !showHistory;
    setShowHistory(next);
    if (next && historicalEvents.length === 0) {
      floodEventsAPI.getEvents()
        .then((res) => setHistoricalEvents(res.data.events || []))
        .catch((error) => console.error('Flood events unavailable:', error));
    }
  };

  const handleMapClick = useCallback((lat, lon) => {
    setQueryPoint({ lat, lon, loading: true });
    riskAPI.getCurrentRisk(lat, lon)
      .then((res) => setQueryPoint({ lat, lon, loading: false, result: res.data }))
      .catch(() => setQueryPoint({ lat, lon, loading: false, error: true }));
  }, []);

  const selectedRisk = useMemo(() => {
    if (!riskLocations.length) return null;
    if (selectedName) {
      const found = riskLocations.find((l) => l.location?.name === selectedName);
      if (found) return found;
    }
    return riskLocations[0];
  }, [riskLocations, selectedName]);

  // Derive real-time values from the selected location's prediction
  const liveOrigin = selectedRisk?.location?.name || 'Kedarnath';
  const liveProbability = selectedRisk?.risk_probability ?? 0;
  const liveRainfallIntensity = selectedRisk?.rainfall?.rainfall_intensity ?? 0;

  // Only fetch propagation when real-time probability is significant
  useEffect(() => {
    if (!liveOrigin || liveProbability < 0.25) {
      setPropagation(null);
      return;
    }
    dynamicsAPI.getPropagation(liveOrigin, liveProbability, Math.max(liveRainfallIntensity, 0.5))
      .then((res) => setPropagation(res.data))
      .catch(() => setPropagation(null));
  }, [liveOrigin, liveProbability, liveRainfallIntensity]);

  return (
    <div className="dashboard">
      <div className="dashboard-map-col">
        <div className="map-toolbar">
          <div className="map-toolbar-status">
            <span className={`status-dot status-dot-${mapStatus === 'error' ? 'offline' : 'online'}`} />
            <span>
              {mapStatus === 'error' ? 'Live data unavailable' : `Live data · updated ${formatClock(lastUpdated)}`}
            </span>
          </div>
          <button type="button" className="toggle-chip" onClick={toggleHistory}>
            {showHistory ? 'Hide history layer' : 'Show history layer'}
          </button>
        </div>

        <div className="map-wrap">
          <FloodMap
            locations={riskLocations}
            selectedLocation={selectedRisk?.location?.name}
            onLocationSelect={(loc) => setSelectedName(loc.location?.name)}
            propagation={propagation}
            onMapClick={handleMapClick}
            queryPoint={queryPoint}
            historicalEvents={showHistory ? historicalEvents : []}
          />
        </div>
        <p className="map-hint">Click anywhere on the map to run a live risk assessment for that exact point.</p>
      </div>

      <div className="dashboard-panel-col">
        <Tabs tabs={TABS} active={activeTab} onChange={setActiveTab} />
        <div className="tab-panel">
          {activeTab === 'risk' && <RiskPanel riskData={selectedRisk} loading={mapStatus === 'loading'} />}
          {activeTab === 'weather' && (
            <>
              <RainfallCard riskData={selectedRisk} />
              <ForecastPanel
                lat={selectedRisk?.location?.lat}
                lon={selectedRisk?.location?.lon}
                label={selectedRisk?.location?.name || selectedRisk?.location?.nearest_station}
              />
            </>
          )}
          {activeTab === 'evac' && (
            <LSETPanel
              origin={liveOrigin}
              probability={liveProbability}
              rainfallIntensity={liveRainfallIntensity}
            />
          )}
          {activeTab === 'infra' && (
            <InfraPanel
              origin={liveOrigin}
              probability={liveProbability}
              rainfallIntensity={liveRainfallIntensity}
            />
          )}
          {activeTab === 'downstream' && (
            <ArrivalTable
              origin={liveOrigin}
              probability={liveProbability}
              rainfallIntensity={liveRainfallIntensity}
            />
          )}
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
