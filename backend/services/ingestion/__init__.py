"""
NeerNetra — Data Ingestion Service
====================================
Handles fetching rainfall, weather, and environmental data from external APIs.
Primary source: Open-Meteo (Phase 2 implementation).
"""


class IngestionService:
    """Service for ingesting weather and rainfall data."""

    async def fetch_current_weather(self, lat: float, lon: float) -> dict:
        """Fetch current weather from Open-Meteo API."""
        raise NotImplementedError("Phase 2: Data Pipeline")

    async def fetch_forecast(self, lat: float, lon: float, hours: int = 48) -> dict:
        """Fetch hourly forecast from Open-Meteo API."""
        raise NotImplementedError("Phase 2: Data Pipeline")

    async def fetch_historical_rainfall(
        self, lat: float, lon: float, start_date: str, end_date: str
    ) -> dict:
        """Fetch historical rainfall data."""
        raise NotImplementedError("Phase 2: Data Pipeline")

    async def compute_rainfall_windows(self, location_id: int) -> dict:
        """Compute rolling rainfall accumulation windows (1h, 3h, 6h, 12h, 24h, 72h)."""
        raise NotImplementedError("Phase 2: Data Pipeline")
