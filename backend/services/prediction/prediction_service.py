"""
NeerNetra -- Prediction Service
==================================
Orchestrates the full prediction pipeline:
  1. Fetch weather data
  2. Compute rainfall features
  3. Load terrain + historical features
  4. Run ML model inference
  5. Run flood dynamics (propagation, cascade, LSET)
  6. Assess confidence
  7. Return unified risk result

This is the primary service called by the API endpoints.
"""
import asyncio
import os
import sys
import json
import numpy as np
from datetime import datetime, timezone
from typing import Optional

import joblib
from sqlalchemy import text
from backend.utils.config import settings
from backend.database.connection import async_session

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.ingestion.weather_client import WeatherClient
from backend.services.ingestion.rainfall_processor import RainfallProcessor
from backend.services.propagation.flood_propagation import FloodPropagationEngine, PILOT_NETWORK
from backend.services.arrival_time.arrival_estimator import ArrivalTimeEstimator
from backend.services.cascade.cascade_analyzer import CascadeAnalyzer
from backend.services.infrastructure.exposure_analyzer import ExposureAnalyzer
from backend.services.lset.lset_calculator import LSETCalculator
from backend.services.prediction.confidence import ConfidenceEstimator
from backend.services.prediction.flood_intensity import FloodIntensityEstimator


# Pilot location lookup
LOCATION_LOOKUP = {loc["name"].lower(): loc for loc in PILOT_NETWORK}

# Static terrain/historical features per location (from Phase 2 data)
STATIC_FEATURES = {
    "kedarnath":   {"elevation": 3583, "slope": 35, "aspect": 180, "terrain_ruggedness": 120,
                    "distance_to_waterbody": 0.3, "historical_flood_frequency": 3,
                    "historical_flood_susceptibility": 0.85, "landslide_susceptibility": 0.85,
                    "distance_to_road": 0.5},
    "gaurikund":   {"elevation": 1982, "slope": 28, "aspect": 200, "terrain_ruggedness": 85,
                    "distance_to_waterbody": 0.1, "historical_flood_frequency": 5,
                    "historical_flood_susceptibility": 0.78, "landslide_susceptibility": 0.78,
                    "distance_to_road": 0.1},
    "sonprayag":   {"elevation": 1829, "slope": 22, "aspect": 190, "terrain_ruggedness": 70,
                    "distance_to_waterbody": 0.1, "historical_flood_frequency": 4,
                    "historical_flood_susceptibility": 0.72, "landslide_susceptibility": 0.72,
                    "distance_to_road": 0.1},
    "rampur":      {"elevation": 1800, "slope": 18, "aspect": 210, "terrain_ruggedness": 55,
                    "distance_to_waterbody": 0.5, "historical_flood_frequency": 2,
                    "historical_flood_susceptibility": 0.55, "landslide_susceptibility": 0.65,
                    "distance_to_road": 0.2},
    "sitapur":     {"elevation": 1600, "slope": 15, "aspect": 220, "terrain_ruggedness": 45,
                    "distance_to_waterbody": 0.4, "historical_flood_frequency": 1,
                    "historical_flood_susceptibility": 0.45, "landslide_susceptibility": 0.55,
                    "distance_to_road": 0.3},
    "agastmuni":   {"elevation": 1000, "slope": 12, "aspect": 160, "terrain_ruggedness": 35,
                    "distance_to_waterbody": 0.2, "historical_flood_frequency": 2,
                    "historical_flood_susceptibility": 0.50, "landslide_susceptibility": 0.45,
                    "distance_to_road": 0.1},
    "rudraprayag": {"elevation":  610, "slope":  8, "aspect": 170, "terrain_ruggedness": 25,
                    "distance_to_waterbody": 0.1, "historical_flood_frequency": 3,
                    "historical_flood_susceptibility": 0.60, "landslide_susceptibility": 0.52,
                    "distance_to_road": 0.05},
    "guptkashi":   {"elevation": 1319, "slope": 20, "aspect": 240, "terrain_ruggedness": 60,
                    "distance_to_waterbody": 0.3, "historical_flood_frequency": 2,
                    "historical_flood_susceptibility": 0.55, "landslide_susceptibility": 0.60,
                    "distance_to_road": 0.2},
    "phata":       {"elevation": 1524, "slope": 25, "aspect": 195, "terrain_ruggedness": 75,
                    "distance_to_waterbody": 0.2, "historical_flood_frequency": 3,
                    "historical_flood_susceptibility": 0.65, "landslide_susceptibility": 0.68,
                    "distance_to_road": 0.1},
    "kalimath":    {"elevation": 1463, "slope": 18, "aspect": 230, "terrain_ruggedness": 50,
                    "distance_to_waterbody": 0.6, "historical_flood_frequency": 2,
                    "historical_flood_susceptibility": 0.50, "landslide_susceptibility": 0.62,
                    "distance_to_road": 0.4},
}


class PredictionService:
    """
    Full prediction pipeline orchestrator.
    """

    def __init__(self):
        self.weather_client = WeatherClient()
        self.rainfall_processor = RainfallProcessor()
        self.propagation = FloodPropagationEngine()
        self.arrival_estimator = ArrivalTimeEstimator()
        self.cascade_analyzer = CascadeAnalyzer()
        self.exposure_analyzer = ExposureAnalyzer()
        self.lset_calculator = LSETCalculator()
        self.confidence_estimator = ConfidenceEstimator()
        self.intensity_estimator = FloodIntensityEstimator()

        self._model = None
        self._model_meta = None
        self._scaler = None
        self._feature_names = None

    def _load_model(self):
        """Load the saved ML model."""
        if self._model is not None:
            return

        model_path = settings.model_path
        model_name = os.path.splitext(os.path.basename(model_path))[0]
        meta_path = os.path.join(os.path.dirname(model_path), f"{model_name}_metadata.json")
        scaler_path = os.path.join(os.path.dirname(model_path), f"{model_name}_scaler.joblib")

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Configured model does not exist: {model_path}")
        self._model = joblib.load(model_path)
        if not os.path.exists(meta_path) or not os.path.exists(scaler_path):
            raise FileNotFoundError(f"Model metadata/scaler missing for {model_path}")
        with open(meta_path, encoding="utf-8") as f:
            self._model_meta = json.load(f)
        self._feature_names = self._model_meta.get("feature_names", [])
        self._scaler = joblib.load(scaler_path)
        expected = len(self._feature_names)
        if getattr(self._model, "n_features_in_", expected) != expected:
            raise RuntimeError(f"Model feature mismatch: model={self._model.n_features_in_}, metadata={expected}")
        if len(self._scaler.get("mean", [])) != expected or len(self._scaler.get("std", [])) != expected:
            raise RuntimeError("Scaler feature count does not match model metadata")

    def _find_nearest_location(self, lat: float, lon: float) -> Optional[str]:
        """Find the nearest pilot location to a coordinate."""
        min_dist = float("inf")
        nearest = None
        for name, loc in LOCATION_LOOKUP.items():
            d = ((lat - loc["lat"])**2 + (lon - loc["lon"])**2) ** 0.5
            if d < min_dist:
                min_dist = d
                nearest = name
        return nearest

    async def predict_risk(self, lat: float, lon: float, db=None) -> dict:
        """
        Full risk prediction for a single location.
        """
        self._load_model()
        location_name = self._find_nearest_location(lat, lon)
        static = STATIC_FEATURES.get(location_name, {})

        # 1. Fetch live weather
        try:
            weather = await self.weather_client.fetch_current_and_forecast(
                lat,
                lon,
                forecast_hours=12,
                past_days=3,
            )
            now = datetime.now(timezone.utc)
            hourly = weather.get("hourly", [])
            recent = {"rainfall_hourly": [
                record for record in hourly
                if record.get("time") and self._record_time(record) <= now
            ]}
            weather["hourly"] = [
                record for record in hourly
                if record.get("time") and self._record_time(record) >= now
            ]

            weather_ok = True

        except Exception as e:
            print(f"Weather fetch failed for {lat}, {lon}: {e}")

            weather = {
                "current": {},
                "hourly": []
            }

            recent = {
                "rainfall_hourly": []
            }

            weather_ok = False

        # 2. Compute rainfall features
        rainfall = self.rainfall_processor.compute_rainfall_features(
            recent.get("rainfall_hourly", [])
        )
        forecast = self.rainfall_processor.compute_forecast_features(
            weather.get("hourly", [])
        )

        current = weather.get("current", {})

        # 3. Assemble feature vector
        features = {
            **rainfall,
            **forecast,
            "temperature": current.get("temperature_2m", 20),
            "humidity": current.get("relative_humidity_2m", 60),
            **static,
            "historical_event_severity": 0.5,
            "blockage_indicator": 0.0,
            "road_exposure_indicator": 0.0,
            "bridge_exposure_indicator": 0.0,
        }

        # 4. Run ML inference
        probability = 0.0
        unavailable_features = []
        if self._model is not None and self._feature_names:
            unavailable_features = [name for name in self._feature_names if name not in features]
            x = self._build_feature_vector(features)
            probability = float(self._model.predict_proba(x)[0, 1])

        risk_level = self._classify_risk(probability)

        # 5. Cascade analysis
        cascade = self.cascade_analyzer.analyze(
            location_name=location_name.title() if location_name else "Unknown",
            rain_6h=rainfall.get("rain_6h", 0),
            rain_24h=rainfall.get("rain_24h", 0),
            slope=static.get("slope", 10),
            landslide_susceptibility=static.get("landslide_susceptibility", 0.5),
            elevation=static.get("elevation", 1000),
            distance_to_waterbody=static.get("distance_to_waterbody", 0.5),
            rainfall_intensity=rainfall.get("rainfall_intensity", 1.0),
        )

        # 6. Confidence
        conf = self.confidence_estimator.estimate(
            model_probability=probability,
            data_age_minutes=5 if weather_ok else 120,
            feature_completeness=0.95 if weather_ok else 0.6,
            terrain_data_available=bool(static),
            historical_data_available=True,
            forecast_available=weather_ok,
        )

        # 7. Flood intensity
        intensity = self.intensity_estimator.estimate_intensity(
            flood_probability=probability,
            rainfall=rainfall,
            forecast=forecast,
            static_features=static,
            cascade=cascade,
        )

        # 8. Determine top drivers
        drivers = self._get_top_drivers(rainfall, cascade, static)

        result = {
            "location": {
                "lat": lat, "lon": lon,
                "nearest_station": location_name.title() if location_name else None,
            },
            "risk_probability": round(probability, 4),
            "risk_level": risk_level,
            "confidence": conf,
            "rainfall": rainfall,
            "forecast": forecast,
            "cascade": cascade,
            "flood_intensity": intensity,
            "drivers": drivers,
            "model_type": settings.model_type,
            "feature_count": len(self._feature_names or []),
            "unavailable_features": unavailable_features,
            "current_weather": {
                "temperature_c": current.get("temperature_2m"),
                "humidity_pct": current.get("relative_humidity_2m"),
                "precipitation_mm": current.get("precipitation"),
            },
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if db is not None and location_name:
            row = await db.execute(text("SELECT id FROM locations WHERE name = :name"), {"name": location_name.title()})
            location_id = row.scalar_one_or_none()
            if location_id is None:
                raise RuntimeError(f"Location is not bootstrapped: {location_name}")
            timestamp = datetime.now(timezone.utc).replace(tzinfo=None)
            await db.execute(
                text("""INSERT INTO predictions
                (location_id, timestamp, probability, risk_level, data_confidence, model_type, drivers)
                VALUES (:location_id, :timestamp, :probability, :risk_level, :confidence, :model_type,
                        CAST(:drivers AS jsonb))
                ON CONFLICT (location_id, timestamp, model_type) DO UPDATE SET
                probability=EXCLUDED.probability, risk_level=EXCLUDED.risk_level,
                data_confidence=EXCLUDED.data_confidence, drivers=EXCLUDED.drivers"""),
                {"location_id": location_id, "timestamp": timestamp, "probability": probability,
                 "risk_level": risk_level, "confidence": conf.get("confidence_level", str(conf)) if isinstance(conf, dict) else str(conf),
                 "model_type": settings.model_type, "drivers": json.dumps(drivers)},
            )
        return result

    async def predict_all_locations(self, db=None) -> list:
        if db is not None:
            async def predict_with_session(name, loc):
                try:
                    async with async_session() as session:
                        result = await self.predict_risk(loc["lat"], loc["lon"], db=session)
                        await session.commit()
                    result["location"]["name"] = name.title()
                    return result
                except Exception as e:
                    return {"location": {"name": name.title(), "lat": loc["lat"], "lon": loc["lon"]}, "error": str(e)}

            return await asyncio.gather(*[
                predict_with_session(name, loc) for name, loc in LOCATION_LOOKUP.items()
            ])

        async def predict_one(name, loc):
            try:
                result = await self.predict_risk(
                    loc["lat"],
                    loc["lon"], db=db
                )

                result["location"]["name"] = name.title()
                return result

            except Exception as e:
                return {
                    "location": {
                        "name": name.title(),
                        "lat": loc["lat"],
                        "lon": loc["lon"],
                    },
                    "error": str(e),
                }

        tasks = [
            predict_one(name, loc)
            for name, loc in LOCATION_LOOKUP.items()
        ]

        return await asyncio.gather(*tasks)

    def _build_feature_vector(self, features: dict) -> np.ndarray:
        """Build a feature vector matching the model's expected order."""
        row = []
        for fname in self._feature_names:
            val = features.get(fname, 0)
            if val is None:
                val = 0
            row.append(float(val))

        x = np.array([row], dtype=np.float32)

        if self._scaler is not None:
            mean = self._scaler.get("mean", np.zeros(len(row)))
            std = self._scaler.get("std", np.ones(len(row)))
            x = (x - mean) / std

        return x

    @staticmethod
    def _record_time(record: dict) -> datetime:
        value = datetime.fromisoformat(record["time"].replace("Z", "+00:00"))
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    @staticmethod
    def _classify_risk(p: float) -> str:
        if p < 0.25: return "LOW"
        elif p < 0.50: return "MEDIUM"
        elif p < 0.75: return "HIGH"
        else: return "CRITICAL"

    @staticmethod
    def _get_top_drivers(rainfall, cascade, static) -> list:
        drivers = []
        if rainfall.get("rain_24h", 0) > 50:
            drivers.append({"factor": "Heavy 24h rainfall", "value": f"{rainfall['rain_24h']}mm"})
        if rainfall.get("rain_6h", 0) > 30:
            drivers.append({"factor": "Intense 6h rainfall", "value": f"{rainfall['rain_6h']}mm"})
        if rainfall.get("rainfall_intensity", 0) > 1.5:
            drivers.append({"factor": "High rainfall intensity", "value": f"{rainfall['rainfall_intensity']}x"})
        if cascade.get("cascade_risk_level") in ("HIGH", "CRITICAL"):
            drivers.append({"factor": "Cascade risk", "value": cascade["cascade_risk_level"]})
        if static.get("landslide_susceptibility", 0) > 0.6:
            drivers.append({"factor": "Landslide susceptibility", "value": f"{static['landslide_susceptibility']}"})
        if static.get("slope", 0) > 25:
            drivers.append({"factor": "Steep terrain", "value": f"{static['slope']} deg"})
        return drivers[:5]
