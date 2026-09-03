-- =============================================================================
-- NeerNetra — PostgreSQL + PostGIS Schema
-- =============================================================================
-- This file is auto-loaded by docker-compose on first database initialization.
-- Matches the ORM models in backend/database/models.py
-- =============================================================================

-- Enable PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;

-- =============================================================================
-- Locations — Monitored points in the pilot region
-- =============================================================================
CREATE TABLE IF NOT EXISTS locations (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,
    latitude        DOUBLE PRECISION NOT NULL,
    longitude       DOUBLE PRECISION NOT NULL,
    elevation       DOUBLE PRECISION,
    slope           DOUBLE PRECISION,
    aspect          DOUBLE PRECISION,
    terrain_ruggedness      DOUBLE PRECISION,
    distance_to_waterbody   DOUBLE PRECISION,
    historical_flood_frequency    INTEGER DEFAULT 0,
    historical_flood_susceptibility DOUBLE PRECISION DEFAULT 0.0,
    landslide_susceptibility      DOUBLE PRECISION DEFAULT 0.0,
    geometry        GEOMETRY(POINT, 4326),
    created_at      TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_locations_geom ON locations USING GIST (geometry);

-- =============================================================================
-- Weather Observations
-- =============================================================================
CREATE TABLE IF NOT EXISTS weather_observations (
    id              SERIAL PRIMARY KEY,
    location_id     INTEGER NOT NULL REFERENCES locations(id),
    timestamp       TIMESTAMP NOT NULL,
    rainfall        DOUBLE PRECISION,
    temperature     DOUBLE PRECISION,
    humidity        DOUBLE PRECISION,
    wind_speed      DOUBLE PRECISION,
    wind_direction  DOUBLE PRECISION,
    weather_code    INTEGER,
    source          VARCHAR(100) DEFAULT 'open-meteo',
    created_at      TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_weather_location_time
    ON weather_observations (location_id, timestamp);

-- =============================================================================
-- Rainfall Features — Pre-computed accumulation windows
-- =============================================================================
CREATE TABLE IF NOT EXISTS rainfall_features (
    id              SERIAL PRIMARY KEY,
    location_id     INTEGER NOT NULL REFERENCES locations(id),
    timestamp       TIMESTAMP NOT NULL,
    rain_1h         DOUBLE PRECISION,
    rain_3h         DOUBLE PRECISION,
    rain_6h         DOUBLE PRECISION,
    rain_12h        DOUBLE PRECISION,
    rain_24h        DOUBLE PRECISION,
    rain_72h        DOUBLE PRECISION,
    rainfall_intensity      DOUBLE PRECISION,
    rainfall_acceleration   DOUBLE PRECISION,
    created_at      TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_rainfall_location_time
    ON rainfall_features (location_id, timestamp);

-- =============================================================================
-- Flood Events — Historical records
-- =============================================================================
CREATE TABLE IF NOT EXISTS flood_events (
    id              SERIAL PRIMARY KEY,
    event_date      TIMESTAMP NOT NULL,
    location_name   VARCHAR(255),
    severity        VARCHAR(50),
    description     TEXT,
    source          VARCHAR(255),
    geometry        GEOMETRY(GEOMETRY, 4326),
    created_at      TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_flood_events_geom ON flood_events USING GIST (geometry);
CREATE INDEX IF NOT EXISTS idx_flood_events_date ON flood_events (event_date);

-- =============================================================================
-- Predictions — ML model outputs
-- =============================================================================
CREATE TABLE IF NOT EXISTS predictions (
    id              SERIAL PRIMARY KEY,
    location_id     INTEGER NOT NULL REFERENCES locations(id),
    timestamp       TIMESTAMP NOT NULL,
    probability     DOUBLE PRECISION NOT NULL,
    risk_level      VARCHAR(50) NOT NULL,
    data_confidence VARCHAR(50),
    model_type      VARCHAR(100) DEFAULT 'random_forest',
    drivers         TEXT,
    created_at      TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_predictions_location_time
    ON predictions (location_id, timestamp);

-- =============================================================================
-- Propagation Results — Time-stepped flood extent
-- =============================================================================
CREATE TABLE IF NOT EXISTS propagation_results (
    id              SERIAL PRIMARY KEY,
    prediction_id   INTEGER NOT NULL REFERENCES predictions(id),
    time_step_minutes INTEGER NOT NULL,
    affected_area   GEOMETRY(MULTIPOLYGON, 4326),
    arrival_time_grid TEXT,
    created_at      TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_propagation_geom
    ON propagation_results USING GIST (affected_area);

-- =============================================================================
-- Infrastructure — Roads and bridges
-- =============================================================================
CREATE TABLE IF NOT EXISTS infrastructure (
    id              SERIAL PRIMARY KEY,
    asset_type      VARCHAR(50) NOT NULL,
    name            VARCHAR(255),
    risk_level      VARCHAR(50),
    estimated_arrival_time TIMESTAMP,
    exposure_duration_minutes INTEGER,
    priority        VARCHAR(50),
    geometry        GEOMETRY(GEOMETRY, 4326),
    created_at      TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_infrastructure_geom
    ON infrastructure USING GIST (geometry);

-- =============================================================================
-- Seed Pilot Region Locations
-- =============================================================================
INSERT INTO locations (name, latitude, longitude, elevation, geometry)
VALUES
    ('Kedarnath',       30.7346, 79.0669, 3583, ST_SetSRID(ST_MakePoint(79.0669, 30.7346), 4326)),
    ('Gaurikund',       30.6560, 79.0900, 1982, ST_SetSRID(ST_MakePoint(79.0900, 30.6560), 4326)),
    ('Sonprayag',       30.6280, 79.0700, 1829, ST_SetSRID(ST_MakePoint(79.0700, 30.6280), 4326)),
    ('Rampur',          30.6350, 79.0520, 1800, ST_SetSRID(ST_MakePoint(79.0520, 30.6350), 4326)),
    ('Sitapur',         30.6100, 79.0400, 1600, ST_SetSRID(ST_MakePoint(79.0400, 30.6100), 4326)),
    ('Agastmuni',       30.5260, 79.0260, 1000, ST_SetSRID(ST_MakePoint(79.0260, 30.5260), 4326)),
    ('Rudraprayag',     30.2840, 78.9800,  610, ST_SetSRID(ST_MakePoint(78.9800, 30.2840), 4326)),
    ('Guptkashi',       30.5300, 79.0700, 1319, ST_SetSRID(ST_MakePoint(79.0700, 30.5300), 4326)),
    ('Phata',           30.5700, 79.0600, 1524, ST_SetSRID(ST_MakePoint(79.0600, 30.5700), 4326)),
    ('Kalimath',        30.5500, 79.0400, 1463, ST_SetSRID(ST_MakePoint(79.0400, 30.5500), 4326))
ON CONFLICT DO NOTHING;
