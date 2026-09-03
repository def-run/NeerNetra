"""
NeerNetra -- Confidence / Uncertainty Estimator
==================================================
Assesses confidence and uncertainty in flood predictions.

From Section 7.3:
  Factors considered:
  1. Input-data completeness
  2. Recency of observations
  3. Similarity to training conditions
  4. Model probability calibration
  5. Agreement between available model signals

Output: A confidence score (0-1) and human-readable level.
"""

from datetime import datetime, timezone
from typing import Optional


class ConfidenceEstimator:
    """
    Estimates prediction confidence based on multiple quality signals.
    """

    def estimate(
        self,
        model_probability: float,
        data_age_minutes: int = 0,
        feature_completeness: float = 1.0,
        rainfall_signal_strength: float = 1.0,
        terrain_data_available: bool = True,
        historical_data_available: bool = True,
        forecast_available: bool = True,
        model_agreement: Optional[float] = None,
    ) -> dict:
        """
        Compute confidence score for a prediction.

        Args:
            model_probability: Raw model output probability (0-1)
            data_age_minutes: How old the latest observation data is
            feature_completeness: Fraction of features that had real values (0-1)
            rainfall_signal_strength: How strong the rainfall signal is
            terrain_data_available: Whether terrain features were from DEM
            historical_data_available: Whether historical flood data was used
            forecast_available: Whether forecast rainfall was available
            model_agreement: Agreement between multiple models (0-1), if available

        Returns:
            dict with confidence_score, confidence_level, and factor breakdown
        """
        factors = {}

        # 1. Data completeness (0-0.25)
        completeness_score = feature_completeness * 0.25
        factors["data_completeness"] = {
            "score": round(completeness_score, 3),
            "value": feature_completeness,
            "status": "good" if feature_completeness > 0.8 else "degraded",
        }

        # 2. Data recency (0-0.20)
        if data_age_minutes <= 15:
            recency_score = 0.20
            recency_status = "fresh"
        elif data_age_minutes <= 60:
            recency_score = 0.15
            recency_status = "recent"
        elif data_age_minutes <= 180:
            recency_score = 0.10
            recency_status = "aging"
        else:
            recency_score = 0.05
            recency_status = "stale"

        factors["data_recency"] = {
            "score": recency_score,
            "age_minutes": data_age_minutes,
            "status": recency_status,
        }

        # 3. Model probability calibration (0-0.20)
        # Higher confidence when probability is clearly high or clearly low
        # Lower confidence for ambiguous middle probabilities
        if model_probability > 0.8 or model_probability < 0.2:
            calibration_score = 0.20
            calibration_status = "clear_signal"
        elif model_probability > 0.65 or model_probability < 0.35:
            calibration_score = 0.15
            calibration_status = "moderate_signal"
        else:
            calibration_score = 0.08
            calibration_status = "ambiguous"

        factors["model_calibration"] = {
            "score": calibration_score,
            "probability": model_probability,
            "status": calibration_status,
        }

        # 4. Data source availability (0-0.20)
        source_score = 0.0
        sources_available = []

        if terrain_data_available:
            source_score += 0.07
            sources_available.append("terrain")
        if historical_data_available:
            source_score += 0.07
            sources_available.append("historical")
        if forecast_available:
            source_score += 0.06
            sources_available.append("forecast")

        factors["data_sources"] = {
            "score": source_score,
            "available": sources_available,
            "status": "complete" if len(sources_available) == 3 else "partial",
        }

        # 5. Model agreement (0-0.15)
        if model_agreement is not None:
            agreement_score = model_agreement * 0.15
            agreement_status = "high" if model_agreement > 0.8 else ("moderate" if model_agreement > 0.5 else "low")
        else:
            agreement_score = 0.08  # Default when only one model
            agreement_status = "single_model"

        factors["model_agreement"] = {
            "score": round(agreement_score, 3),
            "value": model_agreement,
            "status": agreement_status,
        }

        # Compute total confidence
        total = (
            completeness_score +
            recency_score +
            calibration_score +
            source_score +
            agreement_score
        )
        total = min(1.0, total)

        # Confidence level
        if total >= 0.75:
            level = "HIGH"
        elif total >= 0.50:
            level = "MEDIUM"
        elif total >= 0.30:
            level = "LOW"
        else:
            level = "VERY_LOW"

        return {
            "confidence_score": round(total, 3),
            "confidence_level": level,
            "factors": factors,
            "recommendation": self._get_recommendation(level, model_probability),
        }

    @staticmethod
    def _get_recommendation(level: str, probability: float) -> str:
        """Generate a human-readable recommendation based on confidence and risk."""
        if level == "HIGH" and probability > 0.7:
            return "High confidence, high risk. Immediate action recommended."
        elif level == "HIGH" and probability < 0.3:
            return "High confidence, low risk. Continue monitoring."
        elif level in ("LOW", "VERY_LOW"):
            return "Low confidence in prediction. Data quality may be degraded. Exercise caution."
        elif probability > 0.5:
            return "Elevated risk detected. Monitor closely and prepare for potential action."
        else:
            return "Moderate conditions. Continue standard monitoring."
