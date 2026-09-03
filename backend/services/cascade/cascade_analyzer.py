"""
NeerNetra -- Cascade Analyzer
================================
Basic landslide -> blockage -> flood cascade logic.

From Section 7.7:
  High rainfall / terrain conditions
    -> Landslide susceptibility
    -> Possible blockage
    -> Increased downstream flood risk

Implementation uses rule-based thresholds. This is a basic scenario
model, NOT a physically complete landslide simulation.
"""

from typing import Optional


# Thresholds for cascade triggering
RAINFALL_THRESHOLD_6H = 60.0   # mm in 6 hours to consider landslide risk
RAINFALL_THRESHOLD_24H = 120.0  # mm in 24 hours
SLOPE_THRESHOLD = 20.0          # degrees
SUSCEPTIBILITY_THRESHOLD = 0.5  # landslide susceptibility score


class CascadeAnalyzer:
    """
    Evaluates landslide-blockage-flood cascade scenarios.
    """

    def analyze(
        self,
        location_name: str,
        rain_6h: float,
        rain_24h: float,
        slope: float,
        landslide_susceptibility: float,
        elevation: float,
        distance_to_waterbody: float,
        rainfall_intensity: float = 1.0,
    ) -> dict:
        """
        Evaluate the cascade risk chain for a location.

        Chain: Rainfall + Terrain -> Landslide -> Blockage -> Downstream flood increase

        Args:
            location_name: Name of the location
            rain_6h: 6-hour rainfall accumulation (mm)
            rain_24h: 24-hour rainfall accumulation (mm)
            slope: Terrain slope (degrees)
            landslide_susceptibility: Susceptibility score (0-1)
            elevation: Elevation in meters
            distance_to_waterbody: Distance to nearest river/stream (km)
            rainfall_intensity: Current rainfall intensity multiplier

        Returns:
            dict with cascade assessment
        """
        # Step 1: Landslide trigger assessment
        landslide_risk = self._assess_landslide_risk(
            rain_6h, rain_24h, slope, landslide_susceptibility, rainfall_intensity
        )

        # Step 2: Blockage potential (if landslide occurs near water)
        blockage_risk = self._assess_blockage_risk(
            landslide_risk["score"], distance_to_waterbody, elevation
        )

        # Step 3: Downstream flood amplification
        flood_amplification = self._assess_flood_amplification(
            blockage_risk["score"], rain_24h, rainfall_intensity
        )

        # Overall cascade risk
        cascade_score = (
            landslide_risk["score"] * 0.35 +
            blockage_risk["score"] * 0.35 +
            flood_amplification["score"] * 0.30
        )
        cascade_level = self._classify(cascade_score)

        return {
            "location": location_name,
            "cascade_risk_score": round(cascade_score, 3),
            "cascade_risk_level": cascade_level,
            "chain": {
                "landslide_risk": {
                    "score": round(landslide_risk["score"], 3),
                    "level": landslide_risk["level"],
                    "triggers": landslide_risk["triggers"],
                },
                "blockage_risk": {
                    "score": round(blockage_risk["score"], 3),
                    "level": blockage_risk["level"],
                    "factors": blockage_risk["factors"],
                },
                "flood_amplification": {
                    "score": round(flood_amplification["score"], 3),
                    "level": flood_amplification["level"],
                    "downstream_risk_increase_pct": round(
                        flood_amplification["score"] * 30, 1
                    ),
                },
            },
            "blockage_indicator": round(blockage_risk["score"], 3),
            "downstream_risk_modifier": round(1.0 + flood_amplification["score"] * 0.3, 3),
            "disclaimer": "Basic scenario model, not a physically complete landslide simulation.",
        }

    def _assess_landslide_risk(
        self,
        rain_6h: float,
        rain_24h: float,
        slope: float,
        susceptibility: float,
        intensity: float,
    ) -> dict:
        """Assess landslide trigger probability."""
        score = 0.0
        triggers = []

        # Rainfall triggers
        if rain_6h > RAINFALL_THRESHOLD_6H:
            score += 0.25
            triggers.append(f"High 6h rainfall ({rain_6h:.0f}mm > {RAINFALL_THRESHOLD_6H}mm)")
        if rain_24h > RAINFALL_THRESHOLD_24H:
            score += 0.2
            triggers.append(f"High 24h rainfall ({rain_24h:.0f}mm > {RAINFALL_THRESHOLD_24H}mm)")

        # Terrain triggers
        if slope > SLOPE_THRESHOLD:
            score += 0.2
            triggers.append(f"Steep slope ({slope:.0f} deg > {SLOPE_THRESHOLD} deg)")

        # Susceptibility
        if susceptibility > SUSCEPTIBILITY_THRESHOLD:
            score += susceptibility * 0.25
            triggers.append(f"High landslide susceptibility ({susceptibility:.2f})")

        # Intensity boost
        if intensity > 1.5:
            score += 0.1
            triggers.append(f"High rainfall intensity ({intensity:.1f}x)")

        score = min(1.0, score)

        return {
            "score": score,
            "level": self._classify(score),
            "triggers": triggers,
        }

    def _assess_blockage_risk(
        self,
        landslide_score: float,
        distance_to_waterbody: float,
        elevation: float,
    ) -> dict:
        """Assess probability of river/stream blockage from landslide."""
        score = 0.0
        factors = []

        # Blockage requires a landslide near water
        if landslide_score < 0.3:
            return {"score": 0.0, "level": "LOW", "factors": ["Low landslide risk"]}

        # Proximity to water is critical
        if distance_to_waterbody < 0.2:
            score += 0.4
            factors.append(f"Very close to waterbody ({distance_to_waterbody:.1f}km)")
        elif distance_to_waterbody < 0.5:
            score += 0.25
            factors.append(f"Near waterbody ({distance_to_waterbody:.1f}km)")
        elif distance_to_waterbody < 1.0:
            score += 0.1
            factors.append(f"Moderate distance to waterbody ({distance_to_waterbody:.1f}km)")

        # Elevation factor (narrow valleys at mid-elevation more prone to blockage)
        if 1000 < elevation < 3000:
            score += 0.2
            factors.append(f"Mid-elevation valley zone ({elevation:.0f}m)")

        # Scale by landslide probability
        score *= landslide_score
        score = min(1.0, score)

        return {
            "score": score,
            "level": self._classify(score),
            "factors": factors,
        }

    @staticmethod
    def _assess_flood_amplification(
        blockage_score: float,
        rain_24h: float,
        intensity: float,
    ) -> dict:
        """Assess how much a blockage would amplify downstream flooding."""
        if blockage_score < 0.2:
            return {"score": 0.0, "level": "LOW"}

        # Blockage amplifies flood when water accumulates behind it
        score = blockage_score * 0.5

        # More rain = more water behind blockage
        if rain_24h > 150:
            score += 0.3
        elif rain_24h > 100:
            score += 0.2
        elif rain_24h > 50:
            score += 0.1

        # Intensity factor
        score *= (0.7 + 0.3 * min(intensity, 3.0))
        score = min(1.0, score)

        return {"score": score, "level": CascadeAnalyzer._classify(score)}

    @staticmethod
    def _classify(score: float) -> str:
        if score < 0.25:
            return "LOW"
        elif score < 0.50:
            return "MEDIUM"
        elif score < 0.75:
            return "HIGH"
        else:
            return "CRITICAL"
