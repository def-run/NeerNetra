"""
NeerNetra -- Flood Propagation Engine
========================================
Simplified spatial flood propagation over a terrain grid.

From Section 7.5:
  - Use a simplified raster/grid connected drainage representation
  - Start propagation from high-risk upstream cells/areas
  - Apply terrain, drainage connectivity, and configurable propagation speed
  - Store predicted affected cells with time steps
  - Visualise the changing flood footprint on the map

This is a SIMPLIFIED propagation model, not a full hydrodynamic solver.
"""

import numpy as np
from datetime import datetime, timedelta
from typing import Optional
from backend.config.locations import PILOT_LOCATIONS as CANONICAL_LOCATIONS


# Pilot locations ordered upstream -> downstream
LEGACY_PILOT_NETWORK = [
    {"name": "Kedarnath",   "lat": 30.7346, "lon": 79.0669, "elev": 3583, "order": 0},
    {"name": "Gaurikund",   "lat": 30.6560, "lon": 79.0900, "elev": 1982, "order": 1},
    {"name": "Sonprayag",   "lat": 30.6280, "lon": 79.0700, "elev": 1829, "order": 2},
    {"name": "Rampur",      "lat": 30.6350, "lon": 79.0520, "elev": 1800, "order": 3},
    {"name": "Phata",       "lat": 30.5700, "lon": 79.0600, "elev": 1524, "order": 4},
    {"name": "Guptkashi",   "lat": 30.5300, "lon": 79.0700, "elev": 1319, "order": 5},
    {"name": "Kalimath",    "lat": 30.5500, "lon": 79.0400, "elev": 1463, "order": 6},
    {"name": "Agastmuni",   "lat": 30.5260, "lon": 79.0260, "elev": 1000, "order": 7},
    {"name": "Rudraprayag", "lat": 30.2840, "lon": 78.9800, "elev":  610, "order": 8},
]

PILOT_NETWORK = CANONICAL_LOCATIONS

# Default propagation speed in km/h (flash floods in mountain valleys)
DEFAULT_SPEED_KMH = 8.0
# Speed modifier based on slope difference
SLOPE_SPEED_FACTOR = 0.3


class FloodPropagationEngine:
    """
    Simplified flood propagation model using a connected drainage network.

    Propagates flood risk downstream from an origin point using
    terrain elevation differences and configurable speed assumptions.
    """

    def __init__(
        self,
        network: Optional[list] = None,
        base_speed_kmh: float = DEFAULT_SPEED_KMH,
    ):
        self.network = network or PILOT_NETWORK
        self.base_speed_kmh = base_speed_kmh

    def propagate(
        self,
        origin_name: str,
        origin_probability: float,
        start_time: Optional[datetime] = None,
        rainfall_intensity: float = 1.0,
        max_steps: int = 10,
        time_step_minutes: int = 30,
    ) -> dict:
        """
        Propagate flood from an origin location downstream.

        Args:
            origin_name: Name of the origin location
            origin_probability: Flood probability at origin (0-1)
            start_time: When the flood begins (default: now)
            rainfall_intensity: Current rainfall intensity multiplier
            max_steps: Maximum propagation time steps
            time_step_minutes: Minutes per time step

        Returns:
            dict with time-stepped propagation results
        """
        if start_time is None:
            start_time = datetime.utcnow()

        # Find origin in network
        origin = self._find_location(origin_name)
        if origin is None:
            return {"error": f"Location not found: {origin_name}"}

        # Get downstream locations (higher order = further downstream)
        downstream = [
            loc for loc in self.network
            if loc["order"] > origin["order"]
        ]
        downstream.sort(key=lambda x: x["order"])

        # Generate propagation time steps
        time_steps = []
        current_prob = origin_probability
        current_time = start_time

        # Origin step
        time_steps.append({
            "step": 0,
            "time": current_time.isoformat(),
            "minutes_elapsed": 0,
            "affected_locations": [{
                "name": origin["name"],
                "lat": origin["lat"],
                "lon": origin["lon"],
                "elevation": origin["elev"],
                "flood_probability": round(current_prob, 3),
                "risk_level": self._classify_risk(current_prob),
                "status": "origin",
            }],
        })

        # Propagate downstream
        prev_loc = origin
        affected_so_far = [origin]

        for i, downstream_loc in enumerate(downstream):
            if i >= max_steps:
                break

            # Calculate distance between locations
            dist_km = self._haversine(
                prev_loc["lat"], prev_loc["lon"],
                downstream_loc["lat"], downstream_loc["lon"],
            )

            # Calculate propagation speed (steeper = faster)
            elev_diff = prev_loc["elev"] - downstream_loc["elev"]
            slope_factor = 1.0 + SLOPE_SPEED_FACTOR * (elev_diff / max(dist_km * 1000, 1))
            speed = self.base_speed_kmh * max(0.5, min(slope_factor, 3.0))

            # Adjust speed with rainfall intensity
            speed *= (0.8 + 0.4 * min(rainfall_intensity, 3.0))

            # Time to reach this location
            travel_time_hours = dist_km / speed if speed > 0 else float("inf")
            travel_time_minutes = int(travel_time_hours * 60)

            current_time = current_time + timedelta(minutes=travel_time_minutes)

            # Probability decays with distance but increases with slope and rainfall
            distance_decay = max(0.1, 1.0 - (dist_km * 0.03))
            elevation_boost = min(0.2, elev_diff / 5000)
            current_prob = current_prob * distance_decay + elevation_boost
            current_prob *= min(1.5, 0.7 + 0.3 * rainfall_intensity)
            current_prob = max(0, min(1.0, current_prob))

            affected_so_far.append(downstream_loc)

            time_steps.append({
                "step": i + 1,
                "time": current_time.isoformat(),
                "minutes_elapsed": int((current_time - start_time).total_seconds() / 60),
                "affected_locations": [{
                    "name": loc["name"],
                    "lat": loc["lat"],
                    "lon": loc["lon"],
                    "elevation": loc["elev"],
                    "flood_probability": round(
                        current_prob * max(0.5, 1.0 - 0.05 * idx), 3
                    ),
                    "risk_level": self._classify_risk(
                        current_prob * max(0.5, 1.0 - 0.05 * idx)
                    ),
                    "status": "origin" if loc == origin else "propagated",
                } for idx, loc in enumerate(affected_so_far)],
                "propagation_front": {
                    "name": downstream_loc["name"],
                    "distance_from_origin_km": round(
                        self._haversine(
                            origin["lat"], origin["lon"],
                            downstream_loc["lat"], downstream_loc["lon"],
                        ), 2
                    ),
                    "travel_time_minutes": travel_time_minutes,
                    "speed_kmh": round(speed, 1),
                },
            })

            prev_loc = downstream_loc

        return {
            "origin": origin_name,
            "origin_probability": origin_probability,
            "start_time": start_time.isoformat(),
            "total_steps": len(time_steps),
            "total_locations_affected": len(affected_so_far),
            "time_steps": time_steps,
            "model_type": "simplified_drainage_network",
            "disclaimer": "Simplified propagation model, not a full hydrodynamic simulation.",
        }

    def _find_location(self, name: str) -> Optional[dict]:
        for loc in self.network:
            if loc["name"].lower() == name.lower():
                return loc
        return None

    @staticmethod
    def _classify_risk(probability: float) -> str:
        if probability < 0.25:
            return "LOW"
        elif probability < 0.50:
            return "MEDIUM"
        elif probability < 0.75:
            return "HIGH"
        else:
            return "CRITICAL"

    @staticmethod
    def _haversine(lat1, lon1, lat2, lon2) -> float:
        R = 6371.0
        dlat = np.radians(lat2 - lat1)
        dlon = np.radians(lon2 - lon1)
        a = (np.sin(dlat / 2) ** 2 +
             np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) *
             np.sin(dlon / 2) ** 2)
        return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
