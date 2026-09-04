"""
NeerNetra -- Infrastructure Exposure Analyzer
=================================================
Assesses flood exposure for roads and bridges.

From Section 7.8:
  - Road/bridge geometries intersected with flood extent
  - Output: asset type, location, flood-risk level, estimated arrival time,
    exposure duration, priority

For MVP: uses point/line proximity analysis with the flood propagation
footprint. Does not require full raster intersection.
"""

import json
import os
from typing import Optional
from datetime import datetime
from sqlalchemy import text

from backend.services.arrival_time.arrival_estimator import ArrivalTimeEstimator


# Bridge and road data from Phase 2
BRIDGES_FILE = os.path.join("data", "bridges", "kedarnath_bridges.geojson")
ROADS_FILE = os.path.join("data", "roads", "kedarnath_roads.geojson")

# Proximity threshold in km
EXPOSURE_RADIUS_KM = 2.0


class ExposureAnalyzer:
    """
    Analyzes infrastructure exposure to predicted flooding.
    """

    def __init__(self):
        self.arrival_estimator = ArrivalTimeEstimator()
        self._bridges = None
        self._roads = None

    def analyze(
        self,
        origin_name: str,
        origin_probability: float,
        rainfall_intensity: float = 1.0,
        start_time: Optional[datetime] = None,
    ) -> dict:
        """
        Analyze infrastructure exposure for a flood scenario.

        Args:
            origin_name: Where the flood originates
            origin_probability: Flood probability at origin
            rainfall_intensity: Current intensity multiplier
            start_time: When the flood starts

        Returns:
            dict with exposed infrastructure details
        """
        if start_time is None:
            start_time = datetime.utcnow()

        # Get arrival times for all downstream locations
        arrivals = self.arrival_estimator.estimate_for_all_downstream(
            origin_name=origin_name,
            origin_probability=origin_probability,
            rainfall_intensity=rainfall_intensity,
            start_time=start_time,
        )

        # Load infrastructure data
        bridges = self._load_bridges()
        roads = self._load_roads()

        # Assess each bridge
        exposed_bridges = []
        for bridge in bridges:
            exposure = self._assess_bridge_exposure(bridge, arrivals)
            if exposure is not None:
                exposed_bridges.append(exposure)

        # Assess each road segment
        exposed_roads = []
        for road in roads:
            exposure = self._assess_road_exposure(road, arrivals)
            if exposure is not None:
                exposed_roads.append(exposure)

        # Sort by priority
        exposed_bridges.sort(key=lambda x: x.get("priority_score", 0), reverse=True)
        exposed_roads.sort(key=lambda x: x.get("priority_score", 0), reverse=True)

        return {
            "origin": origin_name,
            "origin_probability": origin_probability,
            "exposed_bridges": exposed_bridges,
            "exposed_roads": exposed_roads,
            "total_bridges_at_risk": len(exposed_bridges),
            "total_road_segments_at_risk": len(exposed_roads),
            "critical_assets": [
                a for a in (exposed_bridges + exposed_roads)
                if a.get("risk_level") in ("HIGH", "CRITICAL")
            ],
        }

    async def analyze_from_database(
        self, session, origin_name: str, origin_probability: float,
        rainfall_intensity: float = 1.0, start_time: Optional[datetime] = None,
    ) -> dict:
        """Run the same proximity analysis using PostGIS-seeded assets."""
        rows = await session.execute(text("""SELECT source_id, asset_type, name,
            risk_level, priority, ST_AsGeoJSON(geometry) AS geometry
            FROM infrastructure WHERE geometry IS NOT NULL"""))
        features = []
        for row in rows:
            item = dict(row._mapping)
            geometry = json.loads(item.pop("geometry"))
            features.append({"properties": item, "geometry": geometry})
        bridges = [f for f in features if f["properties"]["asset_type"] == "bridge"]
        roads = [f for f in features if f["properties"]["asset_type"] == "road"]
        arrivals = self.arrival_estimator.estimate_for_all_downstream(
            origin_name=origin_name, origin_probability=origin_probability,
            rainfall_intensity=rainfall_intensity, start_time=start_time or datetime.utcnow(),
        )
        exposed_bridges = [x for x in (self._assess_bridge_exposure(f, arrivals) for f in bridges) if x]
        exposed_roads = [x for x in (self._assess_road_exposure(f, arrivals) for f in roads) if x]
        return {
            "origin": origin_name, "origin_probability": origin_probability,
            "exposed_bridges": exposed_bridges, "exposed_roads": exposed_roads,
            "total_bridges_at_risk": len(exposed_bridges),
            "total_road_segments_at_risk": len(exposed_roads),
            "critical_assets": [a for a in exposed_bridges + exposed_roads
                                if a.get("risk_level") in ("HIGH", "CRITICAL")],
            "data_source": "postgresql/postgis",
        }

    def _assess_bridge_exposure(self, bridge: dict, arrivals: list) -> Optional[dict]:
        """Assess a single bridge's exposure."""
        props = bridge.get("properties", {})
        coords = bridge.get("geometry", {}).get("coordinates", [])

        if len(coords) < 2:
            return None

        b_lon, b_lat = coords[0], coords[1]

        # Find nearest affected location
        nearest = self._find_nearest_arrival(b_lat, b_lon, arrivals)
        if nearest is None or nearest["distance_km"] > EXPOSURE_RADIUS_KM:
            return None

        vulnerability = props.get("flood_vulnerability", "unknown")
        importance = props.get("importance", "unknown")

        priority_score = self._compute_priority(
            vulnerability=vulnerability,
            importance=importance,
            flood_probability=nearest.get("flood_probability", 0),
            distance_km=nearest["distance_km"],
        )

        return {
            "asset_type": "bridge",
            "name": props.get("name", "Unknown Bridge"),
            "bridge_type": props.get("bridge_type", "unknown"),
            "span_m": props.get("span_m"),
            "lat": b_lat,
            "lon": b_lon,
            "nearest_affected_location": nearest.get("location"),
            "distance_to_flood_km": round(nearest["distance_km"], 2),
            "estimated_flood_arrival": nearest.get("estimated_arrival_time"),
            "time_remaining_minutes": nearest.get("time_remaining_minutes"),
            "flood_probability": nearest.get("flood_probability"),
            "risk_level": self._risk_from_vulnerability(
                vulnerability, nearest.get("flood_probability", 0)
            ),
            "vulnerability": vulnerability,
            "importance": importance,
            "priority_score": round(priority_score, 3),
        }

    def _assess_road_exposure(self, road: dict, arrivals: list) -> Optional[dict]:
        """Assess a single road segment's exposure."""
        props = road.get("properties", {})
        coords = road.get("geometry", {}).get("coordinates", [])

        if not coords:
            return None

        # Use midpoint of road for proximity check
        mid_idx = len(coords) // 2
        r_lon, r_lat = coords[mid_idx][0], coords[mid_idx][1]

        nearest = self._find_nearest_arrival(r_lat, r_lon, arrivals)
        if nearest is None or nearest["distance_km"] > EXPOSURE_RADIUS_KM:
            return None

        vulnerability = props.get("flood_vulnerability", "unknown")
        importance = props.get("importance", "unknown")

        priority_score = self._compute_priority(
            vulnerability=vulnerability,
            importance=importance,
            flood_probability=nearest.get("flood_probability", 0),
            distance_km=nearest["distance_km"],
        )

        return {
            "asset_type": "road",
            "name": props.get("name", "Unknown Road"),
            "road_type": props.get("road_type", "unknown"),
            "nearest_affected_location": nearest.get("location"),
            "distance_to_flood_km": round(nearest["distance_km"], 2),
            "estimated_flood_arrival": nearest.get("estimated_arrival_time"),
            "time_remaining_minutes": nearest.get("time_remaining_minutes"),
            "flood_probability": nearest.get("flood_probability"),
            "risk_level": self._risk_from_vulnerability(
                vulnerability, nearest.get("flood_probability", 0)
            ),
            "vulnerability": vulnerability,
            "importance": importance,
            "priority_score": round(priority_score, 3),
        }

    def _find_nearest_arrival(self, lat, lon, arrivals):
        """Find the nearest arrival location to a given point."""
        from backend.services.propagation.flood_propagation import FloodPropagationEngine

        nearest = None
        min_dist = float("inf")
        engine = FloodPropagationEngine()

        for arrival in arrivals:
            if isinstance(arrival, dict) and "error" not in arrival:
                loc_name = arrival.get("location", "")
                loc = engine._find_location(loc_name)
                if loc:
                    d = engine._haversine(lat, lon, loc["lat"], loc["lon"])
                    if d < min_dist:
                        min_dist = d
                        nearest = {**arrival, "distance_km": d}

        return nearest

    @staticmethod
    def _compute_priority(vulnerability, importance, flood_probability, distance_km):
        vuln_scores = {"extreme": 1.0, "very_high": 0.85, "high": 0.7, "medium": 0.4, "low": 0.2}
        imp_scores = {"critical": 1.0, "high": 0.7, "medium": 0.4, "low": 0.2}

        v = vuln_scores.get(vulnerability, 0.3)
        i = imp_scores.get(importance, 0.3)
        proximity = max(0.1, 1.0 - distance_km / EXPOSURE_RADIUS_KM)

        return (v * 0.3 + i * 0.3 + flood_probability * 0.25 + proximity * 0.15)

    @staticmethod
    def _risk_from_vulnerability(vulnerability, probability):
        combined = {"extreme": 0.9, "very_high": 0.8, "high": 0.6, "medium": 0.4, "low": 0.2}
        v = combined.get(vulnerability, 0.3)
        score = v * 0.5 + probability * 0.5

        if score >= 0.7:
            return "CRITICAL"
        elif score >= 0.5:
            return "HIGH"
        elif score >= 0.3:
            return "MEDIUM"
        else:
            return "LOW"

    def _load_bridges(self):
        if self._bridges is None:
            if os.path.exists(BRIDGES_FILE):
                with open(BRIDGES_FILE, "r") as f:
                    data = json.load(f)
                self._bridges = data.get("features", [])
            else:
                self._bridges = []
        return self._bridges

    def _load_roads(self):
        if self._roads is None:
            if os.path.exists(ROADS_FILE):
                with open(ROADS_FILE, "r") as f:
                    data = json.load(f)
                self._roads = data.get("features", [])
            else:
                self._roads = []
        return self._roads
