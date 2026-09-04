"""
NeerNetra — Open-Meteo Weather Client
=======================================
Fetches current weather, hourly forecasts, and historical rainfall
from the Open-Meteo free API (no auth required).

Data source: https://open-meteo.com/en/docs
Format: JSON

This is the primary weather data source for the hackathon MVP (Section 4.2).
"""

import httpx
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional
from backend.utils.config import settings


# ---------------------------------------------------------------------------
# Open-Meteo API Configuration
# ---------------------------------------------------------------------------
BASE_URL = settings.open_meteo_base_url.rstrip("/")
FORECAST_URL = f"{BASE_URL}/forecast"
HISTORICAL_URL = "https://archive-api.open-meteo.com/v1/archive"

# Hourly variables we need for flood prediction (Section 6.3)
HOURLY_VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "rain",
    "weather_code",
    "wind_speed_10m",
    "wind_direction_10m",
    "surface_pressure",
]

# Forecast-specific variables
FORECAST_VARIABLES = HOURLY_VARIABLES + [
    "precipitation_probability",
]


class WeatherClient:
    """
    Async client for Open-Meteo API.

    Provides current weather, hourly forecast, and historical data
    for any lat/lon coordinate.
    """

    def __init__(self, timeout: float = 15.0, retries: int = 2):
        self.timeout = timeout
        self.retries = retries

    async def fetch_current_and_forecast(
        self,
        lat: float,
        lon: float,
        forecast_hours: int = 48,
        past_days: int = 0,
    ) -> dict:
        """
        Fetch current conditions + hourly forecast.

        Args:
            lat: Latitude
            lon: Longitude
            forecast_hours: Number of hours to forecast (default 48)

        Returns:
            dict with 'current' and 'hourly' forecast data
        """
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": ",".join(FORECAST_VARIABLES),
            "current": "temperature_2m,relative_humidity_2m,precipitation,rain,weather_code,wind_speed_10m,wind_direction_10m",
            "timezone": "UTC",
        }
        if past_days:
            params["past_days"] = past_days
            params["forecast_days"] = 1
        else:
            params["forecast_hours"] = forecast_hours

        data = await self._get_json(FORECAST_URL, params)

        return {
            "location": {"lat": lat, "lon": lon},
            "elevation": data.get("elevation"),
            "current": data.get("current", {}),
            "hourly": self._parse_hourly(data.get("hourly", {})),
            "source": "open-meteo",
            "fetched_at": datetime.utcnow().isoformat(),
        }

    async def fetch_historical(
        self,
        lat: float,
        lon: float,
        start_date: str,
        end_date: str,
    ) -> dict:
        """
        Fetch historical hourly weather data.

        Args:
            lat: Latitude
            lon: Longitude
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            dict with hourly historical observations
        """
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": start_date,
            "end_date": end_date,
            "hourly": ",".join(HOURLY_VARIABLES),
            "timezone": "UTC",
        }

        data = await self._get_json(HISTORICAL_URL, params)

        return {
            "location": {"lat": lat, "lon": lon},
            "elevation": data.get("elevation"),
            "hourly": self._parse_hourly(data.get("hourly", {})),
            "period": {"start": start_date, "end": end_date},
            "source": "open-meteo-archive",
            "fetched_at": datetime.utcnow().isoformat(),
        }

    async def fetch_recent_rainfall(
        self,
        lat: float,
        lon: float,
        days_back: int = 7,
    ) -> dict:
        """
        Convenience method: fetch last N days of rainfall data.

        Used for computing rolling rainfall accumulations.
        """
        end_date = datetime.utcnow().strftime("%Y-%m-%d")
        start_date = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%d")

        # Use forecast API for recent days (more reliable for last ~7 days)
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": "precipitation,rain",
            "past_days": days_back,
            "forecast_days": 1,
            "timezone": "UTC",
        }

        data = await self._get_json(FORECAST_URL, params)

        hourly = self._parse_hourly(data.get("hourly", {}))

        return {
            "location": {"lat": lat, "lon": lon},
            "rainfall_hourly": hourly,
            "days_back": days_back,
            "source": "open-meteo",
            "fetched_at": datetime.utcnow().isoformat(),
        }

    async def fetch_for_multiple_locations(
        self,
        locations: list[dict],
        forecast_hours: int = 48,
    ) -> list[dict]:
        """
        Fetch weather for multiple locations concurrently.

        Args:
            locations: List of dicts with 'lat', 'lon', 'name' keys
            forecast_hours: Hours of forecast data

        Returns:
            List of weather results for each location
        """
        results = []
        for loc in locations:
            try:
                data = await self.fetch_current_and_forecast(
                    lat=loc["lat"],
                    lon=loc["lon"],
                    forecast_hours=forecast_hours,
                )
                data["location_name"] = loc.get("name", "Unknown")
                results.append(data)
            except Exception as e:
                results.append({
                    "location": {"lat": loc["lat"], "lon": loc["lon"]},
                    "location_name": loc.get("name", "Unknown"),
                    "error": str(e),
                })
        return results

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------
    async def _get_json(self, url: str, params: dict) -> dict:
        """Fetch JSON with bounded connect/read timeouts and retry backoff."""
        timeout = httpx.Timeout(self.timeout, connect=5.0)
        last_error = None
        for attempt in range(self.retries + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    return response.json()
            except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as exc:
                last_error = exc
                if attempt < self.retries:
                    await asyncio.sleep(0.4 * (attempt + 1))
        raise RuntimeError(f"Open-Meteo request failed after {self.retries + 1} attempts: {last_error}") from last_error

    @staticmethod
    def _parse_hourly(hourly_data: dict) -> list[dict]:
        """
        Convert Open-Meteo's columnar hourly format into row-based records.

        Input:  {"time": [...], "temperature_2m": [...], "precipitation": [...]}
        Output: [{"time": "...", "temperature_2m": ..., "precipitation": ...}, ...]
        """
        if not hourly_data or "time" not in hourly_data:
            return []

        times = hourly_data["time"]
        records = []
        for i, t in enumerate(times):
            record = {"time": t}
            for key, values in hourly_data.items():
                if key != "time" and i < len(values):
                    record[key] = values[i]
            records.append(record)
        return records
