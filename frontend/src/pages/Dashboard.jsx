/**
 * NeerNetra -- Dashboard (Live Map)
 * ===================================
 * The main operational view: live risk map for the 9 pilot locations,
 * click-anywhere risk querying, a flood-scenario control bar, an
 * animated propagation timeline, and a tabbed intel panel.
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import FloodMap from '../maps/FloodMap';
import RiskPanel from '../components/RiskPanel';
import RainfallCard from '../components/RainfallCard';
import ForecastPanel from '../components/ForecastPanel';
import LSETPanel from '../components/LSETPanel';
import InfraPanel from '../components/InfraPanel';
import ArrivalTable from '../components/ArrivalTable';
import PropagationSlider from '../components/PropagationSlider';
import Tabs from '../components/Tabs';
import { riskAPI, dynamicsAPI, systemAPI, floodEventsAPI } from '../services/api';
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

  const [allLocations, setAllLocations] = useState([]);
  const [origin, setOrigin] = useState('Kedarnath');
  const [probability, setProbability] = useState(0.8);
  const [rainfallIntensity, setRainfallIntensity] = useState(1.5);
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

  useEffect(() => {
    systemAPI.getLocations()
      .then((res) => setAllLocations(res.data.locations || []))
      .catch(() => setAllLocations([]));
  }, []);

  useEffect(() => {
    if (!origin) return;
    dynamicsAPI.getPropagation(origin, probability, rainfallIntensity)
      .then((res) => setPropagation(res.data))
      .catch(() => setPropagation(null));
  }, [origin, probability, rainfallIntensity]);

  const toggleHistory = () => {
    const next = !showHistory;
    setShowHistory(next);
    if (next && historicalEvents.length === 0) {
      floodEventsAPI.getEvents()
        .then((res) => setHistoricalEvents(res.data.events || []))
        .catch(() => {});
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

        <div className="panel-card scenario-bar">
          <h3>Flood scenario</h3>
          <div className="scenario-controls">
            <label className="field-label">
              Origin
              <select className="select-input" value={origin} onChange={(e) => setOrigin(e.target.value)}>
                {(allLocations.length ? allLocations : [{ name: origin }]).map((l) => (
                  <option key={l.name} value={l.name}>{l.name}</option>
                ))}
              </select>
            </label>
            <label className="field-label">
              Probability: <span className="field-value">{Math.round(probability * 100)}%</span>
              <input type="range" min={0.1} max={1} step={0.05} value={probability} onChange={(e) => setProbability(Number(e.target.value))} className="range-input" />
            </label>
            <label className="field-label">
              Rain intensity: <span className="field-value">{rainfallIntensity.toFixed(1)}x</span>
              <input type="range" min={0.5} max={3} step={0.1} value={rainfallIntensity} onChange={(e) => setRainfallIntensity(Number(e.target.value))} className="range-input" />
            </label>
          </div>
        </div>

        <PropagationSlider propagation={propagation} />
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
          {activeTab === 'evac' && <LSETPanel origin={origin} probability={probability} rainfallIntensity={rainfallIntensity} />}
          {activeTab === 'infra' && <InfraPanel origin={origin} probability={probability} rainfallIntensity={rainfallIntensity} />}
          {activeTab === 'downstream' && <ArrivalTable origin={origin} probability={probability} rainfallIntensity={rainfallIntensity} />}
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
