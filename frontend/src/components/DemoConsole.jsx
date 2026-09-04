/**
 * NeerNetra -- DemoConsole
 * ==========================
 * Time-stepped replay of the 2013 Kedarnath disaster, driven entirely
 * by the backend simulator (backend/services/simulation/demo_simulator.py).
 * Every control here maps to one /api/demo/* endpoint.
 */

import { useState, useEffect, useCallback } from 'react';
import { demoAPI } from '../services/api';
import { riskColor } from '../utils/constants';

const ALERT_COLORS = {
  WEATHER: '#3FBFAD',
  LANDSLIDE: '#e0a83e',
  FLOOD: '#c4262e',
  EVACUATION: '#e2622d',
  INFRASTRUCTURE: '#9FB3AA',
};

function DemoConsole() {
  const [scenario, setScenario] = useState(null);
  const [state, setState] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    demoAPI.getScenario().then((res) => setScenario(res.data))
      .catch((error) => console.error('Demo scenario unavailable:', error));
    demoAPI.getState().then((res) => setState(res.data))
      .catch((error) => console.error('Demo state unavailable:', error));
  }, []);

  const run = useCallback((fn) => {
    setBusy(true);
    fn().then((res) => setState(res.data.state || res.data)).finally(() => setBusy(false));
  }, []);

  const handleStart = () => run(demoAPI.start);
  const handleAdvance = () => run(demoAPI.advance);
  const handleStep = (n) => run(() => demoAPI.goToStep(n));
  const handleReset = () => {
    setBusy(true);
    demoAPI.stop()
      .then(() => demoAPI.getState())
      .then((res) => setState(res.data))
      .finally(() => setBusy(false));
  };

  if (!scenario) {
    return <div className="panel-card"><div className="loading-pulse">Loading scenario...</div></div>;
  }

  const step = state?.step;
  const sim = state?.simulation;
  const isRunning = sim?.is_running;
  const currentStepNum = sim?.current_step ?? 0;
  const isLast = sim ? currentStepNum >= sim.total_steps - 1 : false;

  return (
    <div className="demo-console">
      <div className="panel-card demo-transport">
        <div className="demo-transport-head">
          <h3>Kedarnath 2013 &mdash; disaster replay</h3>
          <span className="demo-scenario-name">{scenario.scenario}</span>
        </div>
        <p className="tool-desc">
          A scripted, time-stepped replay of the June 2013 disaster showing how the system
          would have escalated in real time, step by step.
        </p>

        <div className="demo-controls">
          {!isRunning ? (
            <button type="button" className="demo-btn demo-btn-primary" onClick={handleStart} disabled={busy}>
              Start simulation
            </button>
          ) : (
            <button type="button" className="demo-btn demo-btn-primary" onClick={handleAdvance} disabled={busy || isLast}>
              {isLast ? 'Scenario complete' : 'Advance ▶'}
            </button>
          )}
          <button type="button" className="demo-btn" onClick={handleReset} disabled={busy}>Reset</button>
        </div>

        <div className="demo-step-chips">
          {scenario.steps.map((s) => (
            <button
              key={s.step}
              type="button"
              className={`demo-chip${currentStepNum === s.step ? ' demo-chip-active' : ''}`}
              style={{ borderColor: riskColor(s.risk_level) }}
              onClick={() => handleStep(s.step)}
              disabled={busy}
              title={s.label}
            >
              {s.step}
            </button>
          ))}
        </div>
      </div>

      {step && (
        <div className="demo-readout" style={{ opacity: busy ? 0.6 : 1 }}>
          <div className="panel-card demo-headline" style={{ borderColor: riskColor(step.risk_level) }}>
            <span className="demo-elapsed">{step.elapsed_display}</span>
            <h2 style={{ color: riskColor(step.risk_level) }}>{step.label}</h2>
            <p>{step.description}</p>
            <div className="demo-headline-stats">
              <div>
                <span className="demo-stat-val" style={{ color: riskColor(step.risk_level) }}>{step.risk_level}</span>
                <span className="demo-stat-label">Flood risk ({Math.round(state.risk.probability * 100)}%)</span>
              </div>
              <div>
                <span className="demo-stat-val" style={{ color: riskColor(state.cascade.cascade_risk_level) }}>
                  {state.cascade.cascade_risk_level}
                </span>
                <span className="demo-stat-label">Cascade risk</span>
              </div>
              <div>
                <span className="demo-stat-val">{state.rainfall.rain_24h}mm</span>
                <span className="demo-stat-label">24h rainfall</span>
              </div>
            </div>
          </div>

          <div className="demo-grid">
            <div className="panel-card">
              <h4>Active alerts</h4>
              {state.alerts.length === 0 && <p className="stub-text">No active alerts.</p>}
              {state.alerts.map((a, i) => (
                <div key={i} className="demo-alert" style={{ borderLeftColor: ALERT_COLORS[a.type] || '#62766d' }}>
                  <span className="demo-alert-type" style={{ color: ALERT_COLORS[a.type] || '#62766d' }}>{a.type}</span>
                  <span>{a.message}</span>
                </div>
              ))}
            </div>

            <div className="panel-card">
              <h4>Propagation</h4>
              {state.propagation.active ? (
                <>
                  <p>Front: <strong>{state.propagation.front}</strong></p>
                  <p>ETA to next location: {state.propagation.eta_minutes} min</p>
                </>
              ) : (
                <p className="stub-text">No active flood propagation yet.</p>
              )}
              <h4 style={{ marginTop: '14px' }}>Infrastructure damage</h4>
              {state.infrastructure_damage.length === 0 ? (
                <p className="stub-text">No reported damage.</p>
              ) : (
                <ul className="demo-damage-list">
                  {state.infrastructure_damage.map((d, i) => <li key={i}>{d}</li>)}
                </ul>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default DemoConsole;
