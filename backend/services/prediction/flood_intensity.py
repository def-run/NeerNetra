"""
NeerNetra -- Flood Intensity Estimator
==========================================
Predicts flood intensity (Low / Moderate / Severe / Extreme) using a
weighted composite score derived from the same features already used
by the binary flood-risk classifier.

Also provides infrastructure withstand assessment: given a flood
intensity and an asset's vulnerability profile, estimate whether the
infrastructure is likely to survive.

This is a rule-based engineering approach (no separate ML model)
because labelled intensity data is not available for training.
"""

from typing import Optional


# ── Intensity thresholds (composite score 0-1) ────────────────────────
INTENSITY_LEVELS = [
    (0.35, "LOW"),
    (0.50, "MODERATE"),
    (0.75, "SEVERE"),
    (1.01, "EXTREME"),
]

# ── Feature weights for composite intensity score ─────────────────────
# Weights sum to ~1.0.  Rainfall-related features dominate because
# they are the strongest short-term predictor of flood magnitude.
WEIGHTS = {
    "flood_probability":              0.18,
    "rainfall_accumulation":          0.22,   # from rain_6h, rain_24h, rain_72h
    "rainfall_intensity":             0.14,
    "terrain_factor":                 0.12,   # slope, ruggedness, elevation proximity
    "historical_susceptibility":      0.10,
    "cascade_risk":                   0.10,
    "forecast_rain":                  0.08,
    "rainfall_acceleration":          0.06,
}


class FloodIntensityEstimator:
    """
    Estimates flood intensity and infrastructure withstand from
    the same feature set used by the risk classifier.
    """

    # ── Public API ────────────────────────────────────────────────────

    def estimate_intensity(
        self,
        flood_probability: float,
        rainfall: dict,
        forecast: dict,
        static_features: dict,
        cascade: Optional[dict] = None,
    ) -> dict:
        """
        Compute a flood intensity assessment.

        Args:
            flood_probability: ML-predicted probability (0-1)
            rainfall: dict with rain_1h … rain_72h, rainfall_intensity, rainfall_acceleration
            forecast: dict with forecast_rain_3h, forecast_rain_6h
            static_features: terrain/historical dict (elevation, slope, etc.)
            cascade: cascade analysis result (optional)

        Returns:
            dict with intensity_level, intensity_score, component scores, description
        """
        components = self._compute_components(
            flood_probability, rainfall, forecast, static_features, cascade,
        )
        score = sum(
            WEIGHTS.get(k, 0) * v for k, v in components.items()
        )
        score = max(0.0, min(1.0, score))
        level = self._classify_intensity(score)

        return {
            "intensity_score": round(score, 4),
            "intensity_level": level,
            "components": {k: round(v, 4) for k, v in components.items()},
            "description": self._describe(level, components),
            "impact_summary": self._impact_summary(level),
        }

    def assess_withstand(
        self,
        intensity_level: str,
        asset_vulnerability: str = "unknown",
        asset_type: str = "unknown",
        importance: str = "unknown",
    ) -> dict:
        """
        Assess whether an infrastructure asset can withstand the flood.

        Returns:
            dict with withstand_status, withstand_score, explanation
        """
        intensity_scores = {"LOW": 0.15, "MODERATE": 0.40, "SEVERE": 0.70, "EXTREME": 0.95}
        vuln_scores = {"low": 0.15, "medium": 0.35, "high": 0.60, "very_high": 0.80, "extreme": 0.95}

        i_score = intensity_scores.get(intensity_level, 0.5)
        v_score = vuln_scores.get(asset_vulnerability, 0.5)

        # Type-based fragility modifier
        type_mod = {"bridge": 0.10, "road": 0.05}.get(asset_type, 0.0)

        # Combined damage likelihood
        damage_score = (i_score * 0.55 + v_score * 0.35 + type_mod * 0.10)
        damage_score = max(0.0, min(1.0, damage_score))

        if damage_score < 0.25:
            status = "LIKELY_SAFE"
            explanation = "Structure expected to withstand this flood level."
        elif damage_score < 0.50:
            status = "AT_RISK"
            explanation = "Moderate damage possible; monitoring recommended."
        elif damage_score < 0.75:
            status = "LIKELY_DAMAGED"
            explanation = "Significant structural damage probable."
        else:
            status = "LIKELY_DESTROYED"
            explanation = "Severe damage or complete failure expected."

        return {
            "withstand_status": status,
            "withstand_score": round(damage_score, 3),
            "explanation": explanation,
            "flood_intensity": intensity_level,
        }

    # ── Internal helpers ──────────────────────────────────────────────

    @staticmethod
    def _compute_components(
        flood_probability, rainfall, forecast, static, cascade,
    ) -> dict:
        """Normalise each feature group to a 0-1 sub-score."""

        # 1. Flood probability (already 0-1)
        prob_score = flood_probability

        # 2. Rainfall accumulation (combine 6h, 24h, 72h)
        r6 = min(rainfall.get("rain_6h", 0) / 100, 1.0)    # 100mm/6h = extreme
        r24 = min(rainfall.get("rain_24h", 0) / 200, 1.0)   # 200mm/24h = extreme
        r72 = min(rainfall.get("rain_72h", 0) / 400, 1.0)   # 400mm/72h = extreme
        accum_score = r6 * 0.4 + r24 * 0.35 + r72 * 0.25

        # 3. Rainfall intensity
        ri = rainfall.get("rainfall_intensity", 0)
        ri_score = min(ri / 3.0, 1.0)                       # 3x = extreme

        # 4. Terrain factor
        slope = static.get("slope", 10)
        ruggedness = static.get("terrain_ruggedness", 30)
        dist_water = static.get("distance_to_waterbody", 1.0)
        slope_score = min(slope / 40, 1.0)
        rugged_score = min(ruggedness / 120, 1.0)
        proximity_score = max(0, 1.0 - dist_water / 1.0)    # <1km = high
        terrain_score = slope_score * 0.45 + rugged_score * 0.30 + proximity_score * 0.25

        # 5. Historical susceptibility
        hist_score = static.get("historical_flood_susceptibility", 0.5)

        # 6. Cascade risk
        if cascade and isinstance(cascade, dict):
            cascade_score_val = cascade.get("cascade_risk_score", 0)
            if isinstance(cascade_score_val, (int, float)):
                cascade_s = min(cascade_score_val, 1.0)
            else:
                cascade_s = 0.3
        else:
            cascade_s = 0.0

        # 7. Forecast rain
        fr3 = min(forecast.get("forecast_rain_3h", 0) / 50, 1.0)
        fr6 = min(forecast.get("forecast_rain_6h", 0) / 100, 1.0)
        forecast_score = fr3 * 0.5 + fr6 * 0.5

        # 8. Rainfall acceleration
        accel = rainfall.get("rainfall_acceleration", 0)
        accel_score = min(max(accel, 0) / 2.0, 1.0)

        return {
            "flood_probability": prob_score,
            "rainfall_accumulation": accum_score,
            "rainfall_intensity": ri_score,
            "terrain_factor": terrain_score,
            "historical_susceptibility": hist_score,
            "cascade_risk": cascade_s,
            "forecast_rain": forecast_score,
            "rainfall_acceleration": accel_score,
        }

    @staticmethod
    def _classify_intensity(score: float) -> str:
        for threshold, level in INTENSITY_LEVELS:
            if score < threshold:
                return level
        return "EXTREME"

    @staticmethod
    def _describe(level: str, components: dict) -> str:
        """Generate a human-readable intensity description."""
        top = sorted(components.items(), key=lambda x: -x[1])[:3]
        factor_names = {
            "flood_probability": "high flood probability",
            "rainfall_accumulation": "heavy cumulative rainfall",
            "rainfall_intensity": "intense rainfall rate",
            "terrain_factor": "steep/rugged terrain",
            "historical_susceptibility": "historically flood-prone area",
            "cascade_risk": "landslide-blockage cascade",
            "forecast_rain": "continued heavy rainfall forecast",
            "rainfall_acceleration": "rapidly increasing rainfall",
        }
        drivers = [factor_names.get(k, k) for k, v in top if v > 0.2]

        descriptions = {
            "LOW": "Minor flooding expected with limited impact.",
            "MODERATE": "Moderate flooding possible. Low-lying areas may be affected.",
            "SEVERE": "Severe flooding expected. Significant risk to infrastructure and safety.",
            "EXTREME": "Extreme, life-threatening flooding. Catastrophic damage likely.",
        }
        desc = descriptions.get(level, "")
        if drivers:
            desc += f" Primary factors: {', '.join(drivers)}."
        return desc

    @staticmethod
    def _impact_summary(level: str) -> dict:
        """Expected impact summary per intensity level."""
        summaries = {
            "LOW": {
                "water_depth": "< 0.3m",
                "flow_velocity": "slow",
                "road_impact": "minor waterlogging",
                "bridge_impact": "safe",
                "evacuation_needed": False,
            },
            "MODERATE": {
                "water_depth": "0.3 – 1.0m",
                "flow_velocity": "moderate",
                "road_impact": "roads may become impassable",
                "bridge_impact": "low-clearance bridges at risk",
                "evacuation_needed": False,
            },
            "SEVERE": {
                "water_depth": "1.0 – 3.0m",
                "flow_velocity": "fast, debris-laden",
                "road_impact": "road damage likely",
                "bridge_impact": "bridges at high risk",
                "evacuation_needed": True,
            },
            "EXTREME": {
                "water_depth": "> 3.0m",
                "flow_velocity": "very fast, catastrophic",
                "road_impact": "road destruction expected",
                "bridge_impact": "bridge failure likely",
                "evacuation_needed": True,
            },
        }
        return summaries.get(level, summaries["LOW"])
