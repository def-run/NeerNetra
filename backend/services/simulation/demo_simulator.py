"""
NeerNetra -- Demo Simulator (Phase 8)
========================================
Simulates the 2013 Kedarnath disaster as a time-stepped scenario.
Provides scripted escalation from normal conditions to catastrophic flood,
allowing judges to see the full system response in real-time.

Scenario Timeline (compressed to ~2 minutes):
  T+0:   Normal conditions, light rain
  T+20s: Rain intensifies, risk rises to MEDIUM
  T+40s: Heavy rain, risk HIGH, cascade triggers begin
  T+60s: Extreme rain, risk CRITICAL, propagation active
  T+80s: Flood reaches Gaurikund, LSET EXPIRED
  T+100s: Flood reaches Sonprayag, infrastructure at risk
  T+120s: Full propagation to Rudraprayag
"""

import time
from datetime import datetime, timedelta, timezone
from typing import Optional


# Simulation timeline: each step represents a "snapshot" of conditions
KEDARNATH_2013_SCENARIO = [
    {
        "step": 0,
        "label": "Normal Conditions",
        "description": "Clear skies, light drizzle. System monitoring.",
        "elapsed_display": "Day 1 - Morning",
        "rain_1h": 2.0, "rain_6h": 8.0, "rain_24h": 15.0, "rain_72h": 25.0,
        "rainfall_intensity": 0.3,
        "temperature": 18.5, "humidity": 65,
        "risk_probability": 0.12, "risk_level": "LOW",
        "cascade_risk": 0.15, "cascade_level": "LOW",
        "active_alerts": [],
        "propagation_active": False,
    },
    {
        "step": 1,
        "label": "Rain Intensifying",
        "description": "Steady rain for 6+ hours. Soil moisture rising.",
        "elapsed_display": "Day 1 - Afternoon",
        "rain_1h": 12.0, "rain_6h": 45.0, "rain_24h": 65.0, "rain_72h": 80.0,
        "rainfall_intensity": 1.2,
        "temperature": 14.2, "humidity": 88,
        "risk_probability": 0.38, "risk_level": "MEDIUM",
        "cascade_risk": 0.35, "cascade_level": "MEDIUM",
        "active_alerts": [
            {"type": "WEATHER", "message": "Heavy rainfall advisory for Mandakini Valley"}
        ],
        "propagation_active": False,
    },
    {
        "step": 2,
        "label": "Heavy Rainfall",
        "description": "Continuous heavy rain. Landslide triggers activating above Kedarnath.",
        "elapsed_display": "Day 1 - Evening",
        "rain_1h": 28.0, "rain_6h": 95.0, "rain_24h": 140.0, "rain_72h": 180.0,
        "rainfall_intensity": 2.1,
        "temperature": 11.0, "humidity": 95,
        "risk_probability": 0.62, "risk_level": "HIGH",
        "cascade_risk": 0.58, "cascade_level": "HIGH",
        "active_alerts": [
            {"type": "WEATHER", "message": "Extreme rainfall warning"},
            {"type": "LANDSLIDE", "message": "Landslide risk HIGH above Kedarnath"},
        ],
        "propagation_active": False,
    },
    {
        "step": 3,
        "label": "CRITICAL -- Cloudburst",
        "description": "Cloudburst detected. Chorabari Tal (glacial lake) water rising rapidly. Flood propagation initiated.",
        "elapsed_display": "Day 2 - Pre-dawn",
        "rain_1h": 45.0, "rain_6h": 160.0, "rain_24h": 230.0, "rain_72h": 310.0,
        "rainfall_intensity": 3.5,
        "temperature": 8.0, "humidity": 99,
        "risk_probability": 0.88, "risk_level": "CRITICAL",
        "cascade_risk": 0.82, "cascade_level": "CRITICAL",
        "active_alerts": [
            {"type": "FLOOD", "message": "CRITICAL: Flash flood imminent at Kedarnath"},
            {"type": "LANDSLIDE", "message": "Multiple landslides reported above Kedarnath"},
            {"type": "EVACUATION", "message": "EVACUATE: Gaurikund, Rambara -- LSET EXPIRED"},
        ],
        "propagation_active": True,
        "propagation_front": "Gaurikund",
        "propagation_eta_min": 35,
    },
    {
        "step": 4,
        "label": "Flood Reaches Gaurikund",
        "description": "Floodwaters have reached Gaurikund. Gaurikund Nala Bridge at CRITICAL risk. Sonprayag has 20 minutes.",
        "elapsed_display": "Day 2 - Dawn",
        "rain_1h": 38.0, "rain_6h": 180.0, "rain_24h": 260.0, "rain_72h": 350.0,
        "rainfall_intensity": 2.8,
        "temperature": 9.5, "humidity": 98,
        "risk_probability": 0.93, "risk_level": "CRITICAL",
        "cascade_risk": 0.91, "cascade_level": "CRITICAL",
        "active_alerts": [
            {"type": "FLOOD", "message": "FLOOD ACTIVE: Gaurikund submerged"},
            {"type": "INFRASTRUCTURE", "message": "Gaurikund Nala Bridge DESTROYED"},
            {"type": "EVACUATION", "message": "EVACUATE NOW: Sonprayag -- 20 min remaining"},
            {"type": "EVACUATION", "message": "PREPARE: Rampur, Phata"},
        ],
        "propagation_active": True,
        "propagation_front": "Sonprayag",
        "propagation_eta_min": 15,
        "infrastructure_damage": ["Gaurikund Nala Bridge", "Rambara Trail"],
    },
    {
        "step": 5,
        "label": "Flood Reaches Sonprayag",
        "description": "Sonprayag Bridge at critical risk. Downstream towns alerted. Rescue operations beginning.",
        "elapsed_display": "Day 2 - Morning",
        "rain_1h": 22.0, "rain_6h": 150.0, "rain_24h": 240.0, "rain_72h": 360.0,
        "rainfall_intensity": 1.8,
        "temperature": 12.0, "humidity": 92,
        "risk_probability": 0.91, "risk_level": "CRITICAL",
        "cascade_risk": 0.88, "cascade_level": "CRITICAL",
        "active_alerts": [
            {"type": "FLOOD", "message": "FLOOD ACTIVE: Gaurikund, Sonprayag"},
            {"type": "INFRASTRUCTURE", "message": "Sonprayag Bridge CRITICAL"},
            {"type": "EVACUATION", "message": "MONITOR: Guptkashi, Agastmuni, Rudraprayag"},
        ],
        "propagation_active": True,
        "propagation_front": "Phata",
        "propagation_eta_min": 36,
        "infrastructure_damage": [
            "Gaurikund Nala Bridge", "Rambara Trail",
            "Sonprayag Bridge", "NH-107 Sonprayag Segment",
        ],
    },
    {
        "step": 6,
        "label": "Full Propagation -- Recovery Phase",
        "description": "Flood has propagated through the valley. Rain subsiding. System tracking recession.",
        "elapsed_display": "Day 2 - Afternoon",
        "rain_1h": 8.0, "rain_6h": 80.0, "rain_24h": 200.0, "rain_72h": 340.0,
        "rainfall_intensity": 0.6,
        "temperature": 15.0, "humidity": 82,
        "risk_probability": 0.55, "risk_level": "HIGH",
        "cascade_risk": 0.45, "cascade_level": "MEDIUM",
        "active_alerts": [
            {"type": "FLOOD", "message": "Flood receding. Debris flow risk remains HIGH."},
            {"type": "INFRASTRUCTURE", "message": "4 bridges damaged, 3 road segments blocked"},
        ],
        "propagation_active": True,
        "propagation_front": "Rudraprayag",
        "propagation_eta_min": 0,
        "infrastructure_damage": [
            "Gaurikund Nala Bridge", "Rambara Trail",
            "Sonprayag Bridge", "NH-107 Sonprayag Segment",
            "Phata Bridge", "Agastmuni Road",
        ],
    },
]


class DemoSimulator:
    """
    Controls the demo simulation state.
    """

    def __init__(self):
        self.scenario = KEDARNATH_2013_SCENARIO
        self.current_step = 0
        self.is_running = False
        self.started_at = None

    def start(self):
        """Start the demo simulation."""
        self.current_step = 0
        self.is_running = True
        self.started_at = datetime.now(timezone.utc)

    def stop(self):
        """Stop and reset the simulation."""
        self.is_running = False
        self.current_step = 0
        self.started_at = None

    def advance(self):
        """Advance to the next step."""
        if self.current_step < len(self.scenario) - 1:
            self.current_step += 1
        return self.get_current_state()

    def go_to_step(self, step: int):
        """Jump to a specific step."""
        self.current_step = max(0, min(step, len(self.scenario) - 1))
        return self.get_current_state()

    def get_current_state(self) -> dict:
        """Get the current simulation state."""
        step_data = self.scenario[self.current_step]

        return {
            "simulation": {
                "is_running": self.is_running,
                "current_step": self.current_step,
                "total_steps": len(self.scenario),
                "started_at": self.started_at.isoformat() if self.started_at else None,
                "scenario": "Kedarnath 2013 Disaster",
            },
            "step": step_data,
            "location": {
                "name": "Kedarnath",
                "lat": 30.7346,
                "lon": 79.0669,
            },
            "risk": {
                "probability": step_data["risk_probability"],
                "level": step_data["risk_level"],
            },
            "rainfall": {
                "rain_1h": step_data["rain_1h"],
                "rain_6h": step_data["rain_6h"],
                "rain_24h": step_data["rain_24h"],
                "rain_72h": step_data["rain_72h"],
                "rainfall_intensity": step_data["rainfall_intensity"],
            },
            "weather": {
                "temperature_c": step_data["temperature"],
                "humidity_pct": step_data["humidity"],
            },
            "cascade": {
                "cascade_risk_score": step_data["cascade_risk"],
                "cascade_risk_level": step_data["cascade_level"],
            },
            "alerts": step_data["active_alerts"],
            "propagation": {
                "active": step_data["propagation_active"],
                "front": step_data.get("propagation_front"),
                "eta_minutes": step_data.get("propagation_eta_min"),
            },
            "infrastructure_damage": step_data.get("infrastructure_damage", []),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
