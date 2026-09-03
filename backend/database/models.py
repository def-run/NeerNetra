"""
NeerNetra — SQLAlchemy ORM Models
==================================
PostGIS-enabled models matching the database schema from Section 11.
"""

from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    Text,
    Index,
)
from geoalchemy2 import Geometry

from database.connection import Base


# =============================================================================
# Locations — Monitored points in the pilot region
# =============================================================================
class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    elevation = Column(Float, nullable=True)
    slope = Column(Float, nullable=True)
    aspect = Column(Float, nullable=True)
    terrain_ruggedness = Column(Float, nullable=True)
    distance_to_waterbody = Column(Float, nullable=True)
    historical_flood_frequency = Column(Integer, default=0)
    historical_flood_susceptibility = Column(Float, default=0.0)
    landslide_susceptibility = Column(Float, default=0.0)
    geometry = Column(Geometry("POINT", srid=4326), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_locations_geom", "geometry", postgresql_using="gist"),
    )


# =============================================================================
# Weather Observations
# =============================================================================
class WeatherObservation(Base):
    __tablename__ = "weather_observations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    rainfall = Column(Float, nullable=True)
    temperature = Column(Float, nullable=True)
    humidity = Column(Float, nullable=True)
    wind_speed = Column(Float, nullable=True)
    wind_direction = Column(Float, nullable=True)
    weather_code = Column(Integer, nullable=True)
    source = Column(String(100), default="open-meteo")
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_weather_location_time", "location_id", "timestamp"),
    )


# =============================================================================
# Rainfall Features — Pre-computed accumulation windows
# =============================================================================
class RainfallFeature(Base):
    __tablename__ = "rainfall_features"

    id = Column(Integer, primary_key=True, autoincrement=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    rain_1h = Column(Float, nullable=True)
    rain_3h = Column(Float, nullable=True)
    rain_6h = Column(Float, nullable=True)
    rain_12h = Column(Float, nullable=True)
    rain_24h = Column(Float, nullable=True)
    rain_72h = Column(Float, nullable=True)
    rainfall_intensity = Column(Float, nullable=True)
    rainfall_acceleration = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_rainfall_location_time", "location_id", "timestamp"),
    )


# =============================================================================
# Flood Events — Historical records
# =============================================================================
class FloodEvent(Base):
    __tablename__ = "flood_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_date = Column(DateTime, nullable=False)
    location_name = Column(String(255), nullable=True)
    severity = Column(String(50), nullable=True)  # LOW, MEDIUM, HIGH, CRITICAL
    description = Column(Text, nullable=True)
    source = Column(String(255), nullable=True)
    geometry = Column(Geometry("GEOMETRY", srid=4326), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_flood_events_geom", "geometry", postgresql_using="gist"),
        Index("idx_flood_events_date", "event_date"),
    )


# =============================================================================
# Predictions — ML model outputs
# =============================================================================
class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    probability = Column(Float, nullable=False)
    risk_level = Column(String(50), nullable=False)  # LOW, MEDIUM, HIGH, CRITICAL
    data_confidence = Column(String(50), nullable=True)  # LOW, MEDIUM, HIGH
    model_type = Column(String(100), default="random_forest")
    drivers = Column(Text, nullable=True)  # JSON string of driving factors
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_predictions_location_time", "location_id", "timestamp"),
    )


# =============================================================================
# Propagation Results — Time-stepped flood extent
# =============================================================================
class PropagationResult(Base):
    __tablename__ = "propagation_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    prediction_id = Column(Integer, ForeignKey("predictions.id"), nullable=False)
    time_step_minutes = Column(Integer, nullable=False)
    affected_area = Column(Geometry("MULTIPOLYGON", srid=4326), nullable=True)
    arrival_time_grid = Column(Text, nullable=True)  # JSON grid
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_propagation_geom", "affected_area", postgresql_using="gist"),
    )


# =============================================================================
# Infrastructure — Roads and bridges
# =============================================================================
class Infrastructure(Base):
    __tablename__ = "infrastructure"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_type = Column(String(50), nullable=False)  # road, bridge
    name = Column(String(255), nullable=True)
    risk_level = Column(String(50), nullable=True)
    estimated_arrival_time = Column(DateTime, nullable=True)
    exposure_duration_minutes = Column(Integer, nullable=True)
    priority = Column(String(50), nullable=True)  # LOW, MEDIUM, HIGH, CRITICAL
    geometry = Column(Geometry("GEOMETRY", srid=4326), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_infrastructure_geom", "geometry", postgresql_using="gist"),
    )
