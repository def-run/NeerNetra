"""
NeerNetra — Data Ingestion Pipeline
======================================
Orchestrates the complete data ingestion workflow:

1. Fetch weather/rainfall from Open-Meteo
2. Compute rainfall accumulation windows
3. Generate/load terrain features from DEM
4. Load infrastructure data
5. Load landslide susceptibility
6. Store everything in PostGIS

This pipeline is triggered by APScheduler (Phase 5) or run manually.
"""

import os
import json
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import text
from backend.database.connection import async_session
from backend.config.locations import PILOT_LOCATIONS as CANONICAL_LOCATIONS

from backend.services.ingestion.weather_client import WeatherClient
from backend.services.ingestion.rainfall_processor import RainfallProcessor


def _parse_naive_dt(iso_str: str) -> datetime:
    """Parse an ISO-8601 string into a naive (no-tz) datetime for TIMESTAMP columns."""
    cleaned = iso_str.replace("Z", "+00:00")
    dt = datetime.fromisoformat(cleaned)
    # Strip timezone — DB columns are naive TIMESTAMP
    return dt.replace(tzinfo=None)


# ---------------------------------------------------------------------------
# Pilot Region Locations
# ---------------------------------------------------------------------------
PILOT_LOCATIONS = [
    {"name": "Kedarnath",    "lat": 30.7346, "lon": 79.0669},
    {"name": "Gaurikund",    "lat": 30.6560, "lon": 79.0900},
    {"name": "Sonprayag",    "lat": 30.6280, "lon": 79.0700},
    {"name": "Rampur",       "lat": 30.6350, "lon": 79.0520},
    {"name": "Sitapur",      "lat": 30.6100, "lon": 79.0400},
    {"name": "Agastmuni",    "lat": 30.5260, "lon": 79.0260},
    {"name": "Rudraprayag",  "lat": 30.2840, "lon": 78.9800},
    {"name": "Guptkashi",    "lat": 30.5300, "lon": 79.0700},
    {"name": "Phata",        "lat": 30.5700, "lon": 79.0600},
    {"name": "Kalimath",     "lat": 30.5500, "lon": 79.0400},
]


class IngestionPipeline:
    """
    Orchestrates weather data fetching and feature computation
    for all pilot region locations.
    """

    def __init__(self):
        self.weather_client = WeatherClient()
        self.rainfall_processor = RainfallProcessor()

    async def run_weather_ingestion(
        self,
        locations: Optional[list[dict]] = None,
        session=None,
    ) -> dict:
        """
        Fetch weather data and compute rainfall features for all locations.

        Returns:
            dict with weather data and rainfall features per location
        """
        locations = locations or CANONICAL_LOCATIONS
        results = {}
        own_session = session is None
        if own_session:
            session = async_session()
        weather_rows_written = 0
        rainfall_rows_written = 0

        for loc in locations:
            name = loc["name"]
            print(f"  Fetching weather for {name} ({loc['lat']}, {loc['lon']})...")

            try:
                # Fetch current weather + forecast
                weather = await self.weather_client.fetch_current_and_forecast(
                    lat=loc["lat"],
                    lon=loc["lon"],
                    forecast_hours=48,
                )

                # Fetch recent rainfall (7 days back)
                recent = await self.weather_client.fetch_recent_rainfall(
                    lat=loc["lat"],
                    lon=loc["lon"],
                    days_back=7,
                )

                # Compute rainfall accumulation windows
                rainfall_features = self.rainfall_processor.compute_rainfall_features(
                    hourly_records=recent.get("rainfall_hourly", []),
                )

                # Compute forecast rainfall features
                forecast_features = self.rainfall_processor.compute_forecast_features(
                    forecast_records=weather.get("hourly", []),
                )

                location_result = await session.execute(
                    text("SELECT id FROM locations WHERE name = :name"), {"name": name}
                )
                location_id = location_result.scalar_one_or_none()
                if location_id is None:
                    raise RuntimeError(f"Location is not bootstrapped: {name}")
                for record in recent.get("rainfall_hourly", []):
                    if not record.get("time"):
                        continue
                    await session.execute(
                        text("""INSERT INTO weather_observations
                        (location_id, timestamp, rainfall, temperature, humidity,
                         wind_speed, wind_direction, weather_code, source)
                        VALUES (:location_id, CAST(:timestamp AS timestamp), :rainfall,
                         :temperature, :humidity, :wind_speed, :wind_direction, :weather_code,
                         'open-meteo')
                        ON CONFLICT (location_id, timestamp, source) DO UPDATE SET
                         rainfall=EXCLUDED.rainfall, temperature=EXCLUDED.temperature,
                         humidity=EXCLUDED.humidity, wind_speed=EXCLUDED.wind_speed,
                         wind_direction=EXCLUDED.wind_direction, weather_code=EXCLUDED.weather_code"""),
                        {"location_id": location_id, "timestamp": _parse_naive_dt(record["time"]),
                         "rainfall": record.get("precipitation", record.get("rain")),
                         "temperature": record.get("temperature_2m"), "humidity": record.get("relative_humidity_2m"),
                         "wind_speed": record.get("wind_speed_10m"), "wind_direction": record.get("wind_direction_10m"),
                         "weather_code": record.get("weather_code")},
                    )
                    weather_rows_written += 1
                feature_time = rainfall_features.get("timestamp")
                if feature_time:
                    await session.execute(
                        text("""INSERT INTO rainfall_features
                        (location_id, timestamp, rain_1h, rain_3h, rain_6h, rain_12h, rain_24h,
                         rain_72h, rainfall_intensity, rainfall_acceleration)
                        VALUES (:location_id, CAST(:timestamp AS timestamp), :rain_1h, :rain_3h,
                         :rain_6h, :rain_12h, :rain_24h, :rain_72h, :intensity, :acceleration)
                        ON CONFLICT (location_id, timestamp) DO UPDATE SET
                         rain_1h=EXCLUDED.rain_1h, rain_3h=EXCLUDED.rain_3h, rain_6h=EXCLUDED.rain_6h,
                         rain_12h=EXCLUDED.rain_12h, rain_24h=EXCLUDED.rain_24h, rain_72h=EXCLUDED.rain_72h,
                         rainfall_intensity=EXCLUDED.rainfall_intensity,
                         rainfall_acceleration=EXCLUDED.rainfall_acceleration"""),
                        {"location_id": location_id, "timestamp": _parse_naive_dt(feature_time),
                         "rain_1h": rainfall_features.get("rain_1h"), "rain_3h": rainfall_features.get("rain_3h"),
                         "rain_6h": rainfall_features.get("rain_6h"), "rain_12h": rainfall_features.get("rain_12h"),
                         "rain_24h": rainfall_features.get("rain_24h"), "rain_72h": rainfall_features.get("rain_72h"),
                         "intensity": rainfall_features.get("rainfall_intensity"),
                         "acceleration": rainfall_features.get("rainfall_acceleration")},
                    )
                    rainfall_rows_written += 1

                results[name] = {
                    "weather": weather,
                    "rainfall_features": rainfall_features,
                    "forecast_features": forecast_features,
                    "status": "success",
                }

            except Exception as e:
                results[name] = {
                    "status": "error",
                    "error": str(e),
                }
                print(f"  [!] Error for {name}: {e}")

        if own_session:
            await session.commit()
            await session.close()
        return {"locations": results, "weather_rows_written": weather_rows_written,
                "rainfall_feature_rows_written": rainfall_rows_written}

    async def run_full_ingestion(self) -> dict:
        """
        Run the complete data ingestion pipeline.

        Steps:
        1. Fetch weather data for all locations
        2. Compute rainfall features
        3. Load terrain features (if DEM available)
        4. Prepare combined feature set

        Returns:
            dict with all ingested data
        """
        print("=" * 60)
        print("NeerNetra — Data Ingestion Pipeline")
        print("=" * 60)

        print("\n[1/3] Fetching weather & rainfall data...")
        ingestion = await self.run_weather_ingestion()
        weather_results = ingestion["locations"]

        print("\n[2/3] Loading terrain features...")
        terrain_results = self._load_terrain_features()

        print("\n[3/3] Loading ancillary data...")
        ancillary = self._load_ancillary_data()

        summary = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "locations_processed": len(PILOT_LOCATIONS),
            "weather_success": sum(
                1 for v in weather_results.values() if v.get("status") == "success"
            ),
            "weather_errors": sum(
                1 for v in weather_results.values() if v.get("status") == "error"
            ),
            "terrain_available": terrain_results is not None,
            "ancillary_loaded": ancillary is not None,
            "weather_rows_written": ingestion["weather_rows_written"],
            "rainfall_feature_rows_written": ingestion["rainfall_feature_rows_written"],
        }

        print(f"\n{'=' * 60}")
        print(f"Pipeline complete: {summary['weather_success']}/{summary['locations_processed']} locations OK")
        print(f"{'=' * 60}")

        return {
            "summary": summary,
            "weather": weather_results,
            "terrain": terrain_results,
            "ancillary": ancillary,
        }

    def _load_terrain_features(self) -> Optional[list]:
        """
        Load pre-computed terrain features for pilot locations.

        Will use DEM processor when DEM is available,
        otherwise uses fallback elevation data.
        """
        dem_path = os.path.join("data", "dem", "kedarnath_synthetic_dem.tif")

        if os.path.exists(dem_path):
            try:
                from geospatial.terrain.dem_processor import DEMProcessor
                from geospatial.terrain.feature_extractor import TerrainFeatureExtractor

                processor = DEMProcessor(dem_path).load()
                extractor = TerrainFeatureExtractor(processor)
                features = extractor.extract_features_for_locations(PILOT_LOCATIONS)
                print(f"  Extracted terrain features for {len(features)} locations from DEM.")
                return features
            except Exception as e:
                print(f"  [!] DEM processing failed: {e}")

        # Fallback: use known elevation data
        print("  Using fallback terrain data (no DEM file found).")
        return self._fallback_terrain_features()

    @staticmethod
    def _fallback_terrain_features() -> list:
        """Provide fallback terrain features from known data."""
        fallback = {
            "Kedarnath":    {"elevation": 3583, "slope": 35, "aspect": 180, "terrain_ruggedness": 120, "distance_to_waterbody": 0.3},
            "Gaurikund":    {"elevation": 1982, "slope": 28, "aspect": 200, "terrain_ruggedness": 85,  "distance_to_waterbody": 0.1},
            "Sonprayag":    {"elevation": 1829, "slope": 22, "aspect": 190, "terrain_ruggedness": 70,  "distance_to_waterbody": 0.1},
            "Rampur":       {"elevation": 1800, "slope": 18, "aspect": 210, "terrain_ruggedness": 55,  "distance_to_waterbody": 0.5},
            "Sitapur":      {"elevation": 1600, "slope": 15, "aspect": 220, "terrain_ruggedness": 45,  "distance_to_waterbody": 0.4},
            "Agastmuni":    {"elevation": 1000, "slope": 12, "aspect": 160, "terrain_ruggedness": 35,  "distance_to_waterbody": 0.2},
            "Rudraprayag":  {"elevation":  610, "slope":  8, "aspect": 170, "terrain_ruggedness": 25,  "distance_to_waterbody": 0.1},
            "Guptkashi":    {"elevation": 1319, "slope": 20, "aspect": 240, "terrain_ruggedness": 60,  "distance_to_waterbody": 0.3},
            "Phata":        {"elevation": 1524, "slope": 25, "aspect": 195, "terrain_ruggedness": 75,  "distance_to_waterbody": 0.2},
            "Kalimath":     {"elevation": 1463, "slope": 18, "aspect": 230, "terrain_ruggedness": 50,  "distance_to_waterbody": 0.6},
        }

        results = []
        for loc in PILOT_LOCATIONS:
            features = fallback.get(loc["name"], {})
            features["name"] = loc["name"]
            features["lat"] = loc["lat"]
            features["lon"] = loc["lon"]
            results.append(features)

        return results

    @staticmethod
    def _load_ancillary_data() -> Optional[dict]:
        """Load landslide susceptibility and other ancillary data."""
        landslide_path = os.path.join("data", "landslides", "kedarnath_landslide_susceptibility.json")

        if not os.path.exists(landslide_path):
            print("  [!] Landslide data not found.")
            return None

        with open(landslide_path, "r") as f:
            data = json.load(f)

        locations = data.get("locations", [])
        print(f"  Loaded landslide susceptibility for {len(locations)} locations.")

        return {
            "landslide_susceptibility": {
                loc["name"]: loc["landslide_susceptibility"]
                for loc in locations
            },
        }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
async def main():
    """Run the ingestion pipeline from command line."""
    pipeline = IngestionPipeline()
    results = await pipeline.run_full_ingestion()

    # Save results to processed data directory
    output_path = os.path.join("data", "processed", "latest_ingestion.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Strip non-serializable data
    summary = results["summary"]
    with open(output_path, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\nSummary saved to: {output_path}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
