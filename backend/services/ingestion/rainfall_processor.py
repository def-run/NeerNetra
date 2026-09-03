"""
NeerNetra — Rainfall Processor
=================================
Computes rolling rainfall accumulation windows from hourly precipitation data.

Windows (Section 6.3):
    rain_1h, rain_3h, rain_6h, rain_12h, rain_24h, rain_72h

Also computes:
    rainfall_intensity     — current rainfall rate relative to recent average
    rainfall_acceleration  — rate of change in rainfall intensity

These are the core environmental features for the ML flood prediction model.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional


class RainfallProcessor:
    """
    Processes hourly rainfall data into rolling accumulation windows
    and derived intensity features.
    """

    # Accumulation windows in hours
    WINDOWS = {
        "rain_1h": 1,
        "rain_3h": 3,
        "rain_6h": 6,
        "rain_12h": 12,
        "rain_24h": 24,
        "rain_72h": 72,
    }

    def compute_rainfall_features(
        self,
        hourly_records: list[dict],
        target_time: Optional[str] = None,
    ) -> dict:
        """
        Compute all rainfall features from hourly precipitation records.

        Args:
            hourly_records: List of dicts with 'time' and 'precipitation'/'rain' keys
            target_time: ISO timestamp to compute features for (default: latest)

        Returns:
            dict with rain_1h..rain_72h, rainfall_intensity, rainfall_acceleration
        """
        if not hourly_records:
            return self._empty_features()

        df = self._to_dataframe(hourly_records)

        if df.empty or "precipitation" not in df.columns:
            return self._empty_features()

        # Use the target time or the latest available
        if target_time:
            target_dt = pd.Timestamp(target_time, tz="UTC")
        else:
            target_dt = df.index.max()

        # Compute accumulation windows
        features = {}
        for name, hours in self.WINDOWS.items():
            window_start = target_dt - pd.Timedelta(hours=hours)
            mask = (df.index > window_start) & (df.index <= target_dt)
            window_data = df.loc[mask, "precipitation"]
            features[name] = round(float(window_data.sum()), 2) if not window_data.empty else 0.0

        # Compute intensity and acceleration
        features["rainfall_intensity"] = self._compute_intensity(df, target_dt)
        features["rainfall_acceleration"] = self._compute_acceleration(df, target_dt)
        features["timestamp"] = target_dt.isoformat()

        return features

    def compute_features_timeseries(
        self,
        hourly_records: list[dict],
    ) -> list[dict]:
        """
        Compute rainfall features for every hour in the dataset.

        Returns a list of feature dicts, one per hour.
        Useful for building the ML training dataset.
        """
        if not hourly_records:
            return []

        df = self._to_dataframe(hourly_records)

        if df.empty or "precipitation" not in df.columns:
            return []

        results = []
        for target_dt in df.index:
            features = {}
            for name, hours in self.WINDOWS.items():
                window_start = target_dt - pd.Timedelta(hours=hours)
                mask = (df.index > window_start) & (df.index <= target_dt)
                window_data = df.loc[mask, "precipitation"]
                features[name] = round(float(window_data.sum()), 2) if not window_data.empty else 0.0

            features["rainfall_intensity"] = self._compute_intensity(df, target_dt)
            features["rainfall_acceleration"] = self._compute_acceleration(df, target_dt)
            features["timestamp"] = target_dt.isoformat()
            results.append(features)

        return results

    def compute_forecast_features(
        self,
        forecast_records: list[dict],
    ) -> dict:
        """
        Compute forecast rainfall accumulation for the next 3h and 6h.

        These features (forecast_rain_3h, forecast_rain_6h) are part of
        the ML input feature set (Section 6.3).
        """
        if not forecast_records:
            return {"forecast_rain_3h": 0.0, "forecast_rain_6h": 0.0}

        df = self._to_dataframe(forecast_records)

        if df.empty or "precipitation" not in df.columns:
            return {"forecast_rain_3h": 0.0, "forecast_rain_6h": 0.0}

        now = df.index.min()

        # Next 3 hours
        mask_3h = (df.index >= now) & (df.index < now + pd.Timedelta(hours=3))
        forecast_3h = float(df.loc[mask_3h, "precipitation"].sum())

        # Next 6 hours
        mask_6h = (df.index >= now) & (df.index < now + pd.Timedelta(hours=6))
        forecast_6h = float(df.loc[mask_6h, "precipitation"].sum())

        return {
            "forecast_rain_3h": round(forecast_3h, 2),
            "forecast_rain_6h": round(forecast_6h, 2),
        }

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------
    @staticmethod
    def _to_dataframe(records: list[dict]) -> pd.DataFrame:
        """Convert hourly records to a time-indexed DataFrame."""
        df = pd.DataFrame(records)

        if "time" in df.columns:
            df["time"] = pd.to_datetime(df["time"], utc=True)
            df = df.set_index("time").sort_index()

        # Ensure precipitation column exists (Open-Meteo uses both names)
        if "precipitation" not in df.columns and "rain" in df.columns:
            df["precipitation"] = df["rain"]

        # Fill NaN with 0 for precipitation
        if "precipitation" in df.columns:
            df["precipitation"] = df["precipitation"].fillna(0.0)

        return df

    @staticmethod
    def _compute_intensity(df: pd.DataFrame, target_dt: pd.Timestamp) -> float:
        """
        Rainfall intensity: ratio of current 1h rain to average 6h rate.

        A value > 1.0 means current rainfall is above the recent average.
        """
        # Current hour rainfall
        hour_start = target_dt - pd.Timedelta(hours=1)
        current_mask = (df.index > hour_start) & (df.index <= target_dt)
        current_rain = float(df.loc[current_mask, "precipitation"].sum()) if current_mask.any() else 0.0

        # Average hourly rate over last 6 hours
        six_h_start = target_dt - pd.Timedelta(hours=6)
        six_h_mask = (df.index > six_h_start) & (df.index <= target_dt)
        six_h_data = df.loc[six_h_mask, "precipitation"]
        avg_rate = float(six_h_data.mean()) if not six_h_data.empty else 0.0

        if avg_rate > 0:
            intensity = round(current_rain / avg_rate, 2)
        else:
            intensity = current_rain  # If no recent rain, raw value is the intensity

        return intensity

    @staticmethod
    def _compute_acceleration(df: pd.DataFrame, target_dt: pd.Timestamp) -> float:
        """
        Rainfall acceleration: difference between recent 3h rate and prior 3h rate.

        Positive = rainfall is increasing (escalating risk).
        Negative = rainfall is decreasing.
        """
        # Recent 3-hour window
        recent_start = target_dt - pd.Timedelta(hours=3)
        recent_mask = (df.index > recent_start) & (df.index <= target_dt)
        recent_rain = float(df.loc[recent_mask, "precipitation"].sum()) if recent_mask.any() else 0.0

        # Prior 3-hour window
        prior_start = target_dt - pd.Timedelta(hours=6)
        prior_mask = (df.index > prior_start) & (df.index <= recent_start)
        prior_rain = float(df.loc[prior_mask, "precipitation"].sum()) if prior_mask.any() else 0.0

        return round(recent_rain - prior_rain, 2)

    @staticmethod
    def _empty_features() -> dict:
        """Return zeroed features when no data is available."""
        return {
            "rain_1h": 0.0,
            "rain_3h": 0.0,
            "rain_6h": 0.0,
            "rain_12h": 0.0,
            "rain_24h": 0.0,
            "rain_72h": 0.0,
            "rainfall_intensity": 0.0,
            "rainfall_acceleration": 0.0,
            "timestamp": None,
        }
