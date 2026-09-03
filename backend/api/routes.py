"""
NeerNetra -- API Routes (Phase 5 -- Full Implementation)
===========================================================
All endpoints are fully wired to the prediction, propagation,
cascade, infrastructure, and LSET services.
"""

import json
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Query, HTTPException

from backend.services.prediction.prediction_service import PredictionService
from backend.services.propagation.flood_propagation import FloodPropagationEngine
from backend.services.arrival_time.arrival_estimator import ArrivalTimeEstimator
from backend.services.cascade.cascade_analyzer import CascadeAnalyzer
from backend.services.infrastructure.exposure_analyzer import ExposureAnalyzer
from backend.services.lset.lset_calculator import LSETCalculator
from backend.services.ingestion.weather_client import WeatherClient
from backend.services.ingestion.rainfall_processor import RainfallProcessor

router = APIRouter()

# Shared service instances
prediction_service = PredictionService()
propagation_engine = FloodPropagationEngine()
arrival_estimator = ArrivalTimeEstimator()
cascade_analyzer = CascadeAnalyzer()
exposure_analyzer = ExposureAnalyzer()
lset_calculator = LSETCalculator()
weather_client = WeatherClient()
rainfall_processor = RainfallProcessor()


# =============================================================================
# Flood Risk
# =============================================================================
@router.get("/risk", tags=["Flood Risk"])
async def get_flood_risk(
    lat: float = Query(..., description="Latitude", ge=-90, le=90),
    lon: float = Query(..., description="Longitude", ge=-180, le=180),
):
    """
    Get current flood risk prediction for a specific location.

    Returns probability, risk level, confidence, and driving factors.
    Uses live Open-Meteo weather data + ML model inference.
    """
    try:
        result = await prediction_service.predict_risk(lat, lon)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/risk-map", tags=["Flood Risk"])
async def get_risk_map():
    """
    Get risk predictions for all pilot region locations.

    Returns an array of risk assessments for the 10 monitored locations.
    """
    try:
        results = await prediction_service.predict_all_locations()
        return {
            "type": "LocationRiskCollection",
            "pilot_region": "Kedarnath / Mandakini Valley",
            "locations": results,
            "total": len(results),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Rainfall & Weather
# =============================================================================
@router.get("/rainfall/current", tags=["Weather"])
async def get_rainfall_current(
    lat: float = Query(..., description="Latitude", ge=-90, le=90),
    lon: float = Query(..., description="Longitude", ge=-180, le=180),
):
    """
    Get current rainfall accumulations for a location.

    Returns rolling rainfall windows (1h through 72h) computed
    from the last 3 days of Open-Meteo data.
    """
    try:
        recent = await weather_client.fetch_recent_rainfall(lat, lon, days_back=3)
        features = rainfall_processor.compute_rainfall_features(
            recent.get("rainfall_hourly", [])
        )
        return {
            "location": {"lat": lat, "lon": lon},
            "rainfall_features": features,
            "source": "Open-Meteo",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/weather/forecast", tags=["Weather"])
async def get_weather_forecast(
    lat: float = Query(..., description="Latitude", ge=-90, le=90),
    lon: float = Query(..., description="Longitude", ge=-180, le=180),
    hours: int = Query(48, description="Forecast hours", ge=1, le=168),
):
    """
    Get hourly weather forecast from Open-Meteo.
    """
    try:
        data = await weather_client.fetch_current_and_forecast(lat, lon, forecast_hours=hours)
        forecast_features = rainfall_processor.compute_forecast_features(
            data.get("hourly", [])
        )
        return {
            "location": {"lat": lat, "lon": lon},
            "elevation_m": data.get("elevation"),
            "current": data.get("current", {}),
            "forecast_rainfall": forecast_features,
            "hourly": data.get("hourly", [])[:hours],
            "source": "Open-Meteo",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Flood Events (Historical)
# =============================================================================
@router.get("/flood-events", tags=["Flood Events"])
async def get_flood_events():
    """
    Get historical flood events for the pilot region.
    """
    events_path = os.path.join("data", "flood_events", "kedarnath_historical_floods.json")
    if not os.path.exists(events_path):
        return {"events": [], "total_count": 0}

    with open(events_path, "r") as f:
        data = json.load(f)

    events = data.get("events", [])
    return {
        "events": events,
        "total_count": len(events),
        "pilot_region": data.get("region", "Kedarnath / Mandakini Valley"),
    }


# =============================================================================
# Flood Propagation
# =============================================================================
@router.get("/propagation", tags=["Flood Dynamics"])
async def get_propagation(
    origin: str = Query(..., description="Origin location name (e.g., Kedarnath)"),
    probability: float = Query(0.8, description="Flood probability at origin", ge=0, le=1),
    rainfall_intensity: float = Query(1.0, description="Rainfall intensity multiplier", ge=0),
):
    """
    Get flood propagation from a specified origin location.

    Returns time-stepped downstream propagation with affected locations,
    speeds, and probabilities.
    """
    result = propagation_engine.propagate(
        origin_name=origin,
        origin_probability=probability,
        rainfall_intensity=rainfall_intensity,
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/arrival-time", tags=["Flood Dynamics"])
async def get_arrival_time(
    origin: str = Query(..., description="Flood origin location"),
    target: str = Query(..., description="Target location"),
    probability: float = Query(0.8, description="Flood probability at origin", ge=0, le=1),
    rainfall_intensity: float = Query(1.0, description="Rainfall intensity", ge=0),
):
    """
    Get estimated flood arrival time at a target location.
    """
    result = arrival_estimator.estimate(
        origin_name=origin,
        target_name=target,
        origin_probability=probability,
        rainfall_intensity=rainfall_intensity,
    )
    return result


@router.get("/arrival-time/all", tags=["Flood Dynamics"])
async def get_all_arrival_times(
    origin: str = Query(..., description="Flood origin location"),
    probability: float = Query(0.8, description="Flood probability at origin", ge=0, le=1),
    rainfall_intensity: float = Query(1.0, description="Rainfall intensity", ge=0),
):
    """
    Get estimated arrival times for ALL downstream locations.
    """
    results = arrival_estimator.estimate_for_all_downstream(
        origin_name=origin,
        origin_probability=probability,
        rainfall_intensity=rainfall_intensity,
    )
    return {"origin": origin, "downstream_arrivals": results}


# =============================================================================
# Cascade Analysis
# =============================================================================
@router.get("/cascade", tags=["Flood Dynamics"])
async def get_cascade_analysis(
    location: str = Query(..., description="Location name"),
    rain_6h: float = Query(0, description="6-hour rainfall (mm)"),
    rain_24h: float = Query(0, description="24-hour rainfall (mm)"),
):
    """
    Get landslide-blockage-flood cascade analysis for a location.
    """
    from backend.services.prediction.prediction_service import STATIC_FEATURES

    static = STATIC_FEATURES.get(location.lower(), {})
    if not static:
        raise HTTPException(status_code=404, detail=f"Location not found: {location}")

    result = cascade_analyzer.analyze(
        location_name=location,
        rain_6h=rain_6h,
        rain_24h=rain_24h,
        slope=static.get("slope", 10),
        landslide_susceptibility=static.get("landslide_susceptibility", 0.5),
        elevation=static.get("elevation", 1000),
        distance_to_waterbody=static.get("distance_to_waterbody", 0.5),
    )
    return result


# =============================================================================
# Infrastructure Risk
# =============================================================================
@router.get("/infrastructure/risk", tags=["Infrastructure"])
async def get_infrastructure_risk(
    origin: str = Query("Kedarnath", description="Flood origin location"),
    probability: float = Query(0.8, description="Flood probability", ge=0, le=1),
    rainfall_intensity: float = Query(1.0, description="Rainfall intensity", ge=0),
):
    """
    Get flood exposure assessment for roads and bridges.
    """
    result = exposure_analyzer.analyze(
        origin_name=origin,
        origin_probability=probability,
        rainfall_intensity=rainfall_intensity,
    )
    return result


# =============================================================================
# LSET (Last Safe Evacuation Time)
# =============================================================================
@router.get("/lset", tags=["Decision Support"])
async def get_lset(
    origin: str = Query(..., description="Flood origin location"),
    target: str = Query(..., description="Target location for LSET"),
    probability: float = Query(0.8, description="Flood probability at origin", ge=0, le=1),
    rainfall_intensity: float = Query(1.0, description="Rainfall intensity", ge=0),
):
    """
    Get Last Safe Evacuation Time for a target location.

    LSET = Estimated Flood Arrival Time - Configured Safety Buffer
    """
    result = lset_calculator.calculate(
        origin_name=origin,
        target_name=target,
        origin_probability=probability,
        rainfall_intensity=rainfall_intensity,
    )
    return result


@router.get("/lset/all", tags=["Decision Support"])
async def get_lset_all(
    origin: str = Query(..., description="Flood origin location"),
    probability: float = Query(0.8, description="Flood probability", ge=0, le=1),
    rainfall_intensity: float = Query(1.0, description="Rainfall intensity", ge=0),
):
    """
    Get LSET for all downstream locations.
    """
    results = lset_calculator.calculate_for_all_downstream(
        origin_name=origin,
        origin_probability=probability,
        rainfall_intensity=rainfall_intensity,
    )
    return {"origin": origin, "lset_results": results}


# =============================================================================
# System / Metadata
# =============================================================================
@router.get("/locations", tags=["System"])
async def get_pilot_locations():
    """
    Get all monitored pilot region locations with metadata.
    """
    from backend.services.prediction.prediction_service import STATIC_FEATURES, LOCATION_LOOKUP

    locations = []
    for name, loc in LOCATION_LOOKUP.items():
        static = STATIC_FEATURES.get(name, {})
        locations.append({
            "name": name.title(),
            "lat": loc["lat"],
            "lon": loc["lon"],
            "elevation": static.get("elevation"),
            "landslide_susceptibility": static.get("landslide_susceptibility"),
            "historical_flood_frequency": static.get("historical_flood_frequency"),
        })

    return {"locations": locations, "total": len(locations)}
