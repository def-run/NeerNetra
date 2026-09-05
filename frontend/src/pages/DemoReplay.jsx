/**
 * NeerNetra -- Demo Replay page
 * ===============================
 * Contains both the Kedarnath 2013 disaster replay (DemoConsole)
 * and the "what-if" scenario simulator with adjustable probability,
 * rainfall, and origin controls.
 */

import { useState, useEffect } from 'react';
import DemoConsole from '../components/DemoConsole';
import PropagationSlider from '../components/PropagationSlider';
import LSETPanel from '../components/LSETPanel';
import InfraPanel from '../components/InfraPanel';
import ArrivalTable from '../components/ArrivalTable';
import Tabs from '../components/Tabs';
import { dynamicsAPI, systemAPI } from '../services/api';

const SIM_TABS = [
  { id: 'evac', label: 'Evacuation' },
  { id: 'infra', label: 'Infrastructure' },
  { id: 'downstream', label: 'Downstream' },
];

function DemoReplay() {
  const [allLocations, setAllLocations] = useState([]);
  const [origin, setOrigin] = useState('Kedarnath');
  const [probability, setProbability] = useState(0.8);
  const [rainfallIntensity, setRainfallIntensity] = useState(1.5);
  const [propagation, setPropagation] = useState(null);
  const [activeTab, setActiveTab] = useState('evac');

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

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>Demo replay</h1>
        <p>Step through the June 2013 Kedarnath disaster as the system would have seen it unfold.</p>
      </div>
      <DemoConsole />

      <div className="page-header" style={{ marginTop: '2rem' }}>
        <h1>Scenario simulator</h1>
        <p>
          Experiment with "what-if" flood scenarios. Adjust the origin, flood probability, and
          rainfall intensity to see how LSET, infrastructure exposure, and downstream arrivals change.
        </p>
      </div>

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

      <Tabs tabs={SIM_TABS} active={activeTab} onChange={setActiveTab} />
      <div className="tab-panel">
        {activeTab === 'evac' && (
          <LSETPanel origin={origin} probability={probability} rainfallIntensity={rainfallIntensity} />
        )}
        {activeTab === 'infra' && (
          <InfraPanel origin={origin} probability={probability} rainfallIntensity={rainfallIntensity} />
        )}
        {activeTab === 'downstream' && (
          <ArrivalTable origin={origin} probability={probability} rainfallIntensity={rainfallIntensity} />
        )}
      </div>
    </div>
  );
}

export default DemoReplay;
