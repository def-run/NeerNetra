"""Central application configuration loaded from .env or process environment."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://neernetra:neernetra_dev_2026@localhost:5432/neernetra"
    pilot_region_name: str = "Kedarnath"
    pilot_region_lat: float = 30.735
    pilot_region_lon: float = 79.066
    pilot_region_bbox_north: float = 30.85
    pilot_region_bbox_south: float = 30.60
    pilot_region_bbox_east: float = 79.20
    pilot_region_bbox_west: float = 78.90
    open_meteo_base_url: str = "https://api.open-meteo.com/v1"
    prediction_interval_minutes: int = 30
    data_refresh_interval_minutes: int = 15
    model_path: str = "ml/saved_models/flood_random_forest.joblib"
    model_type: str = "random_forest"
    log_level: str = "INFO"
    debug: bool = False
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"
    db_auto_init: bool = False

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore",
        protected_namespaces=("settings_",)
    )


settings = Settings()
