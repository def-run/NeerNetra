"""Fast, local checks for the executable architecture contracts."""

from pathlib import Path

import pandas as pd
from backend.database import models
from backend.config.locations import PILOT_LOCATIONS
from backend.services.prediction.prediction_service import PredictionService
from backend.utils.config import settings
from ml.data.dataset_generator import generate_dataset


def test_canonical_location_registry():
    assert len(PILOT_LOCATIONS) == 10
    assert len({location["name"] for location in PILOT_LOCATIONS}) == 10


def test_model_metadata_matches_runtime():
    service = PredictionService()
    service._load_model()
    assert service._model.n_features_in_ == len(service._feature_names) == 25
    assert len(service._scaler["mean"]) == len(service._scaler["std"]) == 25
    assert Path(settings.model_path).exists()


def test_synthetic_generator_respects_declared_range():
    dataset = generate_dataset(100, seed=7, start_date="2018-01-01", end_date="2026-06-30")
    assert dataset["timestamp"].min() >= pd.Timestamp("2018-01-01")
    assert dataset["timestamp"].max() <= pd.Timestamp("2026-06-30")


def test_orm_uses_package_import_and_unique_keys():
    assert models.Location.__table__.constraints
    assert models.WeatherObservation.__table__.constraints
    assert models.FloodEvent.__table__.constraints
