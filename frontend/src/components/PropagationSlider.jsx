/**
 * NeerNetra -- PropagationSlider
 * ================================
 * Animated time slider for stepping through flood propagation from
 * the chosen origin.
 */

import { useState, useEffect, useRef } from 'react';
import { riskColor, formatPct } from '../utils/constants';

function PropagationSlider({ propagation }) {
  const [currentStep, setCurrentStep] = useState(0);
  const [playing, setPlaying] = useState(false);
  const intervalRef = useRef(null);

  const steps = propagation?.time_steps || [];
  const maxStep = Math.max(0, steps.length - 1);

  useEffect(() => {
    setCurrentStep(0);
    setPlaying(false);
  }, [propagation?.origin, propagation?.origin_probability]);

  useEffect(() => {
    if (playing && steps.length > 1) {
      intervalRef.current = setInterval(() => {
        setCurrentStep((prev) => (prev >= maxStep ? 0 : prev + 1));
      }, 1400);
    }
    return () => clearInterval(intervalRef.current);
  }, [playing, maxStep, steps.length]);

  if (!propagation || steps.length === 0) return null;

  const step = steps[currentStep] || {};
  const front = step.propagation_front;
  const affected = step.affected_locations || [];

  return (
    <div className="panel-card propagation-slider">
      <div className="risk-header">
        <h3>Flood propagation</h3>
        <span className="slider-affected">{propagation.total_locations_affected} locations affected</span>
      </div>

      <div className="slider-control">
        <button className="slider-btn" type="button" onClick={() => setPlaying((p) => !p)} aria-label={playing ? 'Pause' : 'Play'}>
          {playing ? '❚❚' : '▶'}
        </button>
        <input
          type="range"
          min={0}
          max={maxStep}
          value={currentStep}
          onChange={(e) => { setCurrentStep(Number(e.target.value)); setPlaying(false); }}
          className="slider-range"
        />
        <span className="slider-step-label">{currentStep}/{maxStep}</span>
      </div>

      <div className="slider-step-info">
        <span className="slider-time">+{step.minutes_elapsed || 0} min</span>
        {front && <span className="slider-front">Front: {front.name} &middot; {front.speed_kmh} km/h</span>}
      </div>

      <div className="slider-locations">
        {affected.map((loc, i) => (
          <div key={i} className="slider-loc-item" style={{ borderLeftColor: riskColor(loc.risk_level || 'LOW') }}>
            <span>{loc.name}</span>
            <span className="slider-loc-prob">{formatPct(loc.flood_probability)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default PropagationSlider;
