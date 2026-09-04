"""PostgreSQL/PostGIS ORM models used by the runtime services."""

from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, JSON
from sqlalchemy import String, Text, UniqueConstraint

from backend.database.connection import Base


class Location(Base):
    __tablename__ = "locations"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    elevation = Column(Float)
    slope = Column(Float)
    aspect = Column(Float)
    terrain_ruggedness = Column(Float)
    distance_to_waterbody = Column(Float)
    historical_flood_frequency = Column(Integer, default=0)
    historical_flood_susceptibility = Column(Float, default=0.0)
    landslide_susceptibility = Column(Float, default=0.0)
    geometry = Column(Geometry("POINT", srid=4326))
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (
        Index("idx_locations_geom", "geometry", postgresql_using="gist"),
        UniqueConstraint("name", name="uq_locations_name"),
    )


class WeatherObservation(Base):
    __tablename__ = "weather_observations"
    id = Column(Integer, primary_key=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    rainfall = Column(Float)
    temperature = Column(Float)
    humidity = Column(Float)
    wind_speed = Column(Float)
    wind_direction = Column(Float)
    weather_code = Column(Integer)
    source = Column(String(100), default="open-meteo", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (
        Index("idx_weather_location_time", "location_id", "timestamp"),
        UniqueConstraint("location_id", "timestamp", "source", name="uq_weather_observation"),
    )


class RainfallFeature(Base):
    __tablename__ = "rainfall_features"
    id = Column(Integer, primary_key=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    rain_1h = Column(Float)
    rain_3h = Column(Float)
    rain_6h = Column(Float)
    rain_12h = Column(Float)
    rain_24h = Column(Float)
    rain_72h = Column(Float)
    rainfall_intensity = Column(Float)
    rainfall_acceleration = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (
        Index("idx_rainfall_location_time", "location_id", "timestamp"),
        UniqueConstraint("location_id", "timestamp", name="uq_rainfall_feature"),
    )


class FloodEvent(Base):
    __tablename__ = "flood_events"
    id = Column(Integer, primary_key=True)
    source_id = Column(String(100), nullable=False)
    event_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime)
    location_name = Column(String(255))
    severity = Column(String(50))
    flood_type = Column(String(100))
    estimated_rainfall_24h_mm = Column(Float)
    estimated_rainfall_72h_mm = Column(Float)
    deaths = Column(Integer)
    description = Column(Text)
    source = Column(String(255))
    affected_locations = Column(JSON)
    geometry = Column(Geometry("GEOMETRY", srid=4326))
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (
        Index("idx_flood_events_geom", "geometry", postgresql_using="gist"),
        Index("idx_flood_events_date", "event_date"),
        UniqueConstraint("source_id", name="uq_flood_events_source_id"),
    )


class Prediction(Base):
    __tablename__ = "predictions"
    id = Column(Integer, primary_key=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    probability = Column(Float, nullable=False)
    risk_level = Column(String(50), nullable=False)
    data_confidence = Column(String(50))
    model_type = Column(String(100), nullable=False)
    drivers = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (
        Index("idx_predictions_location_time", "location_id", "timestamp"),
        UniqueConstraint("location_id", "timestamp", "model_type", name="uq_prediction_run"),
    )


class PropagationResult(Base):
    __tablename__ = "propagation_results"
    id = Column(Integer, primary_key=True)
    prediction_id = Column(Integer, ForeignKey("predictions.id"), nullable=False)
    time_step_minutes = Column(Integer, nullable=False)
    affected_area = Column(Geometry("MULTIPOLYGON", srid=4326))
    arrival_time_grid = Column(JSON)
    result_data = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (
        Index("idx_propagation_geom", "affected_area", postgresql_using="gist"),
        UniqueConstraint("prediction_id", "time_step_minutes", name="uq_propagation_step"),
    )


class Infrastructure(Base):
    __tablename__ = "infrastructure"
    id = Column(Integer, primary_key=True)
    source_id = Column(String(100), nullable=False)
    asset_type = Column(String(50), nullable=False)
    name = Column(String(255))
    risk_level = Column(String(50))
    estimated_arrival_time = Column(DateTime)
    exposure_duration_minutes = Column(Integer)
    priority = Column(String(50))
    geometry = Column(Geometry("GEOMETRY", srid=4326))
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (
        Index("idx_infrastructure_geom", "geometry", postgresql_using="gist"),
        UniqueConstraint("source_id", name="uq_infrastructure_source_id"),
    )
