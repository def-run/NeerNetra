"""
NeerNetra — Feature Builder
==============================
Assembles ML-ready feature vectors from raw data sources.

Takes the combined dataset and produces clean, normalized feature
matrices ready for model training and inference.

Feature groups (Section 6.3):
  Environmental (12): rain windows, forecasts, intensity, acceleration, temp, humidity
  Terrain (5): elevation, slope, aspect, ruggedness, distance_to_waterbody
  Historical (3): flood_frequency, event_severity, flood_susceptibility
  Cascade (5): landslide_suscept, blockage, distance_to_road, road_exposure, bridge_exposure

Total: 25 features → flood_event target
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional


# ---------------------------------------------------------------------------
# Feature Column Definitions
# ---------------------------------------------------------------------------
ENVIRONMENTAL_FEATURES = [
    "rain_1h", "rain_3h", "rain_6h", "rain_12h", "rain_24h", "rain_72h",
    "forecast_rain_3h", "forecast_rain_6h",
    "rainfall_intensity", "rainfall_acceleration",
    "temperature", "humidity",
]

TERRAIN_FEATURES = [
    "elevation", "slope", "aspect", "terrain_ruggedness",
    "distance_to_waterbody",
]

HISTORICAL_FEATURES = [
    "historical_flood_frequency", "historical_event_severity",
    "historical_flood_susceptibility",
]

CASCADE_FEATURES = [
    "landslide_susceptibility", "blockage_indicator",
    "distance_to_road", "road_exposure_indicator", "bridge_exposure_indicator",
]

ALL_FEATURES = ENVIRONMENTAL_FEATURES + TERRAIN_FEATURES + HISTORICAL_FEATURES + CASCADE_FEATURES

TARGET_COLUMN = "flood_event"

METADATA_COLUMNS = ["timestamp", "location_name"]


class FeatureBuilder:
    """
    Builds ML-ready feature matrices from raw datasets.
    """

    def __init__(self, feature_columns: Optional[list] = None):
        self.feature_columns = feature_columns or ALL_FEATURES
        self._scaler_params = None

    def prepare_features(
        self,
        df: pd.DataFrame,
        fit_scaler: bool = False,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Extract feature matrix X and target vector y from a DataFrame.

        Args:
            df: DataFrame with all feature columns and target
            fit_scaler: If True, compute and store scaling parameters

        Returns:
            (X, y) tuple of numpy arrays
        """
        # Validate columns
        missing = [c for c in self.feature_columns if c not in df.columns]
        if missing:
            raise ValueError(f"Missing feature columns: {missing}")

        X = df[self.feature_columns].copy()
        y = df[TARGET_COLUMN].values.astype(int)

        # Handle missing values
        X = X.fillna(0)

        # Handle infinity
        X = X.replace([np.inf, -np.inf], 0)

        if fit_scaler:
            self._fit_scaler(X)

        if self._scaler_params is not None:
            X = self._apply_scaler(X)

        return X.values.astype(np.float32), y

    def prepare_single(self, features: dict) -> np.ndarray:
        """
        Prepare a single observation for inference.

        Args:
            features: dict with feature values

        Returns:
            1D numpy array ready for model.predict()
        """
        row = []
        for col in self.feature_columns:
            val = features.get(col, 0)
            if val is None or (isinstance(val, float) and np.isnan(val)):
                val = 0
            row.append(float(val))

        x = np.array([row], dtype=np.float32)

        if self._scaler_params is not None:
            means = self._scaler_params["mean"]
            stds = self._scaler_params["std"]
            x = (x - means) / stds

        return x

    def get_feature_names(self) -> list:
        """Get ordered feature names."""
        return list(self.feature_columns)

    def get_feature_groups(self) -> dict:
        """Get features grouped by category."""
        return {
            "environmental": ENVIRONMENTAL_FEATURES,
            "terrain": TERRAIN_FEATURES,
            "historical": HISTORICAL_FEATURES,
            "cascade": CASCADE_FEATURES,
        }

    # -----------------------------------------------------------------------
    # Scaling
    # -----------------------------------------------------------------------
    def _fit_scaler(self, X: pd.DataFrame):
        """Compute mean and std for standardization."""
        self._scaler_params = {
            "mean": X.mean().values.astype(np.float32),
            "std": X.std().values.astype(np.float32),
        }
        # Avoid division by zero
        self._scaler_params["std"] = np.where(
            self._scaler_params["std"] == 0, 1.0, self._scaler_params["std"]
        )

    def _apply_scaler(self, X: pd.DataFrame) -> pd.DataFrame:
        """Apply standardization."""
        means = self._scaler_params["mean"]
        stds = self._scaler_params["std"]
        return (X - means) / stds

    @property
    def scaler_params(self) -> Optional[dict]:
        """Get scaler parameters for saving alongside model."""
        return self._scaler_params

    def set_scaler_params(self, params: dict):
        """Set scaler parameters (for loading a saved model)."""
        self._scaler_params = params
