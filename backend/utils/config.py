"""
NeerNetra — Configuration
==========================
Application settings loaded from environment variables.
"""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # --- Database ---
    database_url: str = "postgresql+asyncpg://neernetra:neernetra_dev_2026@localhost:5432/neernetra"

    # --- Pilot Region ---
    pilot_region_name: str = "Kedarnath"
    pilot_region_lat: float = 30.735
    pilot_region_lon: float = 79.066
    pilot_region_bbox_north: float = 30.85
    pilot_region_bbox_south: float = 30.60
    pilot_region_bbox_east: float = 79.20
    pilot_region_bbox_west: float = 78.90

    # --- Open-Meteo ---
    open_meteo_base_url: str = "https://api.open-meteo.com/v1"

    # --- Scheduling ---
    prediction_interval_minutes: int = 30
    data_refresh_interval_minutes: int = 15

    # --- ML ---
    model_path: str = "ml/saved_models/flood_rf_model.joblib"
    model_type: str = "random_forest"

    # --- App ---
    log_level: str = "INFO"
    debug: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
