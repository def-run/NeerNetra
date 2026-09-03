"""
NeerNetra -- Flood Arrival Time Estimator
============================================
Estimates when flooding may reach a specific downstream location.

From Section 7.6:
  - Predicted flood arrival time
  - Time remaining until estimated arrival
  - Arrival-time confidence/quality indicator

The arrival-time output feeds the infrastructure-risk and LSET modules.
"""

import numpy as np
from datetime import datetime, timedelta
from typing import Optional

from backend.services.propagation.flood_propagation import (
    FloodPropagationEngine,
    PILOT_NETWORK,
)


class ArrivalTimeEstimator:
    """
    Estimates flood arrival time for downstream locations.
    """

    def __init__(self):
        self.propagation = FloodPropagationEngine()

    def estimate(
        self,
        origin_name: str,
        target_name: str,
        origin_probability: float,
        rainfall_intensity: float = 1.0,
        start_time: Optional[datetime] = None,
    ) -> dict:
        """
        Estimate flood arrival time at a target location.

        Args:
            origin_name: Where the flood originates
            target_name: Where we want the arrival estimate
            origin_probability: Flood probability at origin
            rainfall_intensity: Current rainfall intensity multiplier
            start_time: When the flood begins

        Returns:
            dict with arrival time, time remaining, and confidence
        """
        if start_time is None:
            start_time = datetime.utcnow()

        # Run propagation
        result = self.propagation.propagate(
            origin_name=origin_name,
            origin_probability=origin_probability,
            start_time=start_time,
            rainfall_intensity=rainfall_intensity,
        )

        if "error" in result:
            return result

        # Find the target in the propagation steps
        arrival_step = None
        for step in result.get("time_steps", []):
            front = step.get("propagation_front", {})
            if front.get("name", "").lower() == target_name.lower():
                arrival_step = step
                break

        if arrival_step is None:
            return {
                "origin": origin_name,
                "target": target_name,
                "estimated_arrival_time": None,
                "time_remaining_minutes": None,
                "message": f"{target_name} is not downstream of {origin_name} in the network.",
                "confidence": "LOW",
            }

        arrival_time = datetime.fromisoformat(arrival_step["time"])
        now = datetime.utcnow()
        remaining = max(0, int((arrival_time - now).total_seconds() / 60))

        front = arrival_step.get("propagation_front", {})

        # Confidence based on distance, probability, and data quality
        confidence = self._assess_confidence(
            origin_probability=origin_probability,
            distance_km=front.get("distance_from_origin_km", 0),
            rainfall_intensity=rainfall_intensity,
        )

        return {
            "origin": origin_name,
            "target": target_name,
            "estimated_arrival_time": arrival_time.isoformat(),
            "time_remaining_minutes": remaining,
            "travel_time_minutes": arrival_step.get("minutes_elapsed", 0),
            "distance_from_origin_km": front.get("distance_from_origin_km"),
            "propagation_speed_kmh": front.get("speed_kmh"),
            "flood_probability_at_target": self._get_target_prob(arrival_step, target_name),
            "risk_level_at_target": self._get_target_risk(arrival_step, target_name),
            "confidence": confidence,
            "disclaimer": "Arrival time is an estimate, not a guarantee.",
        }

    def estimate_for_all_downstream(
        self,
        origin_name: str,
        origin_probability: float,
        rainfall_intensity: float = 1.0,
        start_time: Optional[datetime] = None,
    ) -> list:
        """
        Estimate arrival times for ALL locations downstream of the origin.

        Returns:
            List of arrival estimates, ordered by arrival time
        """
        if start_time is None:
            start_time = datetime.utcnow()

        result = self.propagation.propagate(
            origin_name=origin_name,
            origin_probability=origin_probability,
            start_time=start_time,
            rainfall_intensity=rainfall_intensity,
        )

        if "error" in result:
            return [result]

        estimates = []
        for step in result.get("time_steps", []):
            front = step.get("propagation_front")
            if front is None:
                continue

            arrival_time = datetime.fromisoformat(step["time"])
            now = datetime.utcnow()
            remaining = max(0, int((arrival_time - now).total_seconds() / 60))

            confidence = self._assess_confidence(
                origin_probability=origin_probability,
                distance_km=front.get("distance_from_origin_km", 0),
                rainfall_intensity=rainfall_intensity,
            )

            estimates.append({
                "location": front["name"],
                "estimated_arrival_time": arrival_time.isoformat(),
                "time_remaining_minutes": remaining,
                "travel_time_minutes": step.get("minutes_elapsed", 0),
                "distance_km": front.get("distance_from_origin_km"),
                "speed_kmh": front.get("speed_kmh"),
                "flood_probability": self._get_target_prob(step, front["name"]),
                "confidence": confidence,
            })

        return estimates

    @staticmethod
    def _assess_confidence(
        origin_probability: float,
        distance_km: float,
        rainfall_intensity: float,
    ) -> str:
        """
        Assess confidence in the arrival time estimate.

        Higher confidence when:
        - High flood probability at origin
        - Short distance (less uncertainty)
        - Clear rainfall signal
        """
        score = 0.0

        # Probability signal strength
        if origin_probability > 0.75:
            score += 0.4
        elif origin_probability > 0.50:
            score += 0.25
        else:
            score += 0.1

        # Distance factor (closer = more confident)
        if distance_km < 10:
            score += 0.3
        elif distance_km < 30:
            score += 0.2
        else:
            score += 0.1

        # Rainfall clarity
        if rainfall_intensity > 2.0:
            score += 0.3
        elif rainfall_intensity > 1.0:
            score += 0.2
        else:
            score += 0.1

        if score >= 0.7:
            return "HIGH"
        elif score >= 0.5:
            return "MEDIUM"
        else:
            return "LOW"

    @staticmethod
    def _get_target_prob(step: dict, target_name: str) -> Optional[float]:
        for loc in step.get("affected_locations", []):
            if loc["name"].lower() == target_name.lower():
                return loc.get("flood_probability")
        return None

    @staticmethod
    def _get_target_risk(step: dict, target_name: str) -> Optional[str]:
        for loc in step.get("affected_locations", []):
            if loc["name"].lower() == target_name.lower():
                return loc.get("risk_level")
        return None
