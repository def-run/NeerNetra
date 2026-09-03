"""
NeerNetra -- LSET Calculator
================================
Last Safe Evacuation Time estimation.

From Section 7.9:
  LSET = Estimated Flood Arrival Time - Configured Safety Buffer

  Show:
  - Estimated arrival time
  - LSET
  - Buffer assumption
  - Confidence level

  This is a PLANNING ESTIMATE, NOT a guarantee.
"""

from datetime import datetime, timedelta
from typing import Optional

from backend.services.arrival_time.arrival_estimator import ArrivalTimeEstimator


# Default safety buffer in minutes
# Accounts for decision time + evacuation logistics
DEFAULT_SAFETY_BUFFER_MINUTES = 30

# Location-specific buffer overrides (higher for harder-to-evacuate areas)
LOCATION_BUFFERS = {
    "Kedarnath":   60,   # Remote, high altitude, limited egress
    "Gaurikund":   45,   # End of road, trail only
    "Sonprayag":   30,   # Road access but narrow
    "Rampur":      30,
    "Phata":       25,
    "Guptkashi":   20,   # Town, multiple routes
    "Kalimath":    30,   # Side valley
    "Agastmuni":   20,   # Good road access
    "Rudraprayag": 15,   # Town, multiple routes
}


class LSETCalculator:
    """
    Calculates Last Safe Evacuation Time for locations.
    """

    def __init__(self):
        self.arrival_estimator = ArrivalTimeEstimator()

    def calculate(
        self,
        origin_name: str,
        target_name: str,
        origin_probability: float,
        rainfall_intensity: float = 1.0,
        safety_buffer_minutes: Optional[int] = None,
        start_time: Optional[datetime] = None,
    ) -> dict:
        """
        Calculate LSET for a target location.

        Args:
            origin_name: Flood origin
            target_name: Location to calculate LSET for
            origin_probability: Flood probability at origin
            rainfall_intensity: Current rainfall intensity
            safety_buffer_minutes: Override default buffer (location-specific used if None)
            start_time: When the flood begins

        Returns:
            dict with LSET, arrival time, buffer, and confidence
        """
        if start_time is None:
            start_time = datetime.utcnow()

        # Get safety buffer for this location
        if safety_buffer_minutes is None:
            safety_buffer_minutes = LOCATION_BUFFERS.get(
                target_name, DEFAULT_SAFETY_BUFFER_MINUTES
            )

        # Get arrival time estimate
        arrival = self.arrival_estimator.estimate(
            origin_name=origin_name,
            target_name=target_name,
            origin_probability=origin_probability,
            rainfall_intensity=rainfall_intensity,
            start_time=start_time,
        )

        if arrival.get("estimated_arrival_time") is None:
            return {
                "target": target_name,
                "lset": None,
                "estimated_arrival_time": None,
                "message": arrival.get("message", "Cannot compute LSET."),
                "confidence": "LOW",
            }

        arrival_time = datetime.fromisoformat(arrival["estimated_arrival_time"])
        lset_time = arrival_time - timedelta(minutes=safety_buffer_minutes)

        now = datetime.utcnow()
        time_until_lset = max(0, int((lset_time - now).total_seconds() / 60))
        time_until_arrival = max(0, int((arrival_time - now).total_seconds() / 60))

        # Urgency classification
        if time_until_lset <= 0:
            urgency = "EXPIRED"
        elif time_until_lset <= 15:
            urgency = "EVACUATE_NOW"
        elif time_until_lset <= 30:
            urgency = "PREPARE_EVACUATION"
        elif time_until_lset <= 60:
            urgency = "ALERT"
        else:
            urgency = "MONITOR"

        return {
            "target": target_name,
            "origin": origin_name,
            "lset": lset_time.isoformat(),
            "estimated_arrival_time": arrival_time.isoformat(),
            "time_until_lset_minutes": time_until_lset,
            "time_until_arrival_minutes": time_until_arrival,
            "safety_buffer_minutes": safety_buffer_minutes,
            "urgency": urgency,
            "flood_probability": arrival.get("flood_probability_at_target"),
            "confidence": arrival.get("confidence", "LOW"),
            "distance_from_origin_km": arrival.get("distance_from_origin_km"),
            "disclaimer": "PLANNING ESTIMATE. NOT a guarantee. Evacuate immediately if instructed by authorities.",
        }

    def calculate_for_all_downstream(
        self,
        origin_name: str,
        origin_probability: float,
        rainfall_intensity: float = 1.0,
        start_time: Optional[datetime] = None,
    ) -> list:
        """
        Calculate LSET for all downstream locations.

        Returns:
            List of LSET results, ordered by urgency (most urgent first)
        """
        if start_time is None:
            start_time = datetime.utcnow()

        arrivals = self.arrival_estimator.estimate_for_all_downstream(
            origin_name=origin_name,
            origin_probability=origin_probability,
            rainfall_intensity=rainfall_intensity,
            start_time=start_time,
        )

        results = []
        for arrival in arrivals:
            if "error" in arrival:
                continue

            target_name = arrival.get("location", "")
            buffer = LOCATION_BUFFERS.get(target_name, DEFAULT_SAFETY_BUFFER_MINUTES)

            arrival_time_str = arrival.get("estimated_arrival_time")
            if arrival_time_str is None:
                continue

            arrival_time = datetime.fromisoformat(arrival_time_str)
            lset_time = arrival_time - timedelta(minutes=buffer)

            now = datetime.utcnow()
            time_until_lset = max(0, int((lset_time - now).total_seconds() / 60))

            if time_until_lset <= 0:
                urgency = "EXPIRED"
            elif time_until_lset <= 15:
                urgency = "EVACUATE_NOW"
            elif time_until_lset <= 30:
                urgency = "PREPARE_EVACUATION"
            elif time_until_lset <= 60:
                urgency = "ALERT"
            else:
                urgency = "MONITOR"

            results.append({
                "location": target_name,
                "lset": lset_time.isoformat(),
                "estimated_arrival": arrival_time.isoformat(),
                "time_until_lset_minutes": time_until_lset,
                "safety_buffer_minutes": buffer,
                "urgency": urgency,
                "flood_probability": arrival.get("flood_probability"),
                "confidence": arrival.get("confidence", "LOW"),
            })

        # Sort by urgency (most urgent first)
        urgency_order = {"EXPIRED": 0, "EVACUATE_NOW": 1, "PREPARE_EVACUATION": 2, "ALERT": 3, "MONITOR": 4}
        results.sort(key=lambda x: urgency_order.get(x.get("urgency", "MONITOR"), 5))

        return results
