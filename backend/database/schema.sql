CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS locations (
    id SERIAL PRIMARY KEY, name VARCHAR(255) NOT NULL UNIQUE,
    latitude DOUBLE PRECISION NOT NULL, longitude DOUBLE PRECISION NOT NULL,
    elevation DOUBLE PRECISION, slope DOUBLE PRECISION, aspect DOUBLE PRECISION,
    terrain_ruggedness DOUBLE PRECISION, distance_to_waterbody DOUBLE PRECISION,
    historical_flood_frequency INTEGER DEFAULT 0,
    historical_flood_susceptibility DOUBLE PRECISION DEFAULT 0,
    landslide_susceptibility DOUBLE PRECISION DEFAULT 0,
    geometry GEOMETRY(POINT, 4326), created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_locations_geom ON locations USING GIST (geometry);

CREATE TABLE IF NOT EXISTS weather_observations (
    id SERIAL PRIMARY KEY, location_id INTEGER NOT NULL REFERENCES locations(id),
    timestamp TIMESTAMP NOT NULL, rainfall DOUBLE PRECISION,
    temperature DOUBLE PRECISION, humidity DOUBLE PRECISION,
    wind_speed DOUBLE PRECISION, wind_direction DOUBLE PRECISION,
    weather_code INTEGER, source VARCHAR(100) NOT NULL DEFAULT 'open-meteo',
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT uq_weather_observation UNIQUE (location_id, timestamp, source)
);
CREATE INDEX IF NOT EXISTS idx_weather_location_time ON weather_observations(location_id, timestamp);

CREATE TABLE IF NOT EXISTS rainfall_features (
    id SERIAL PRIMARY KEY, location_id INTEGER NOT NULL REFERENCES locations(id),
    timestamp TIMESTAMP NOT NULL, rain_1h DOUBLE PRECISION, rain_3h DOUBLE PRECISION,
    rain_6h DOUBLE PRECISION, rain_12h DOUBLE PRECISION, rain_24h DOUBLE PRECISION,
    rain_72h DOUBLE PRECISION, rainfall_intensity DOUBLE PRECISION,
    rainfall_acceleration DOUBLE PRECISION, created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT uq_rainfall_feature UNIQUE (location_id, timestamp)
);
CREATE INDEX IF NOT EXISTS idx_rainfall_location_time ON rainfall_features(location_id, timestamp);

CREATE TABLE IF NOT EXISTS flood_events (
    id SERIAL PRIMARY KEY, source_id VARCHAR(100) NOT NULL UNIQUE,
    event_date TIMESTAMP NOT NULL, end_date TIMESTAMP, location_name VARCHAR(255),
    severity VARCHAR(50), flood_type VARCHAR(100),
    estimated_rainfall_24h_mm DOUBLE PRECISION, estimated_rainfall_72h_mm DOUBLE PRECISION,
    deaths INTEGER, description TEXT, source VARCHAR(255), affected_locations JSONB,
    geometry GEOMETRY(GEOMETRY, 4326), created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_flood_events_geom ON flood_events USING GIST(geometry);

CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY, location_id INTEGER NOT NULL REFERENCES locations(id),
    timestamp TIMESTAMP NOT NULL, probability DOUBLE PRECISION NOT NULL,
    risk_level VARCHAR(50) NOT NULL, data_confidence VARCHAR(50),
    model_type VARCHAR(100) NOT NULL, drivers JSONB, created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT uq_prediction_run UNIQUE (location_id, timestamp, model_type)
);
CREATE INDEX IF NOT EXISTS idx_predictions_location_time ON predictions(location_id, timestamp);

CREATE TABLE IF NOT EXISTS propagation_results (
    id SERIAL PRIMARY KEY, prediction_id INTEGER NOT NULL REFERENCES predictions(id),
    time_step_minutes INTEGER NOT NULL, affected_area GEOMETRY(MULTIPOLYGON, 4326),
    arrival_time_grid JSONB, result_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT uq_propagation_step UNIQUE (prediction_id, time_step_minutes)
);
CREATE INDEX IF NOT EXISTS idx_propagation_geom ON propagation_results USING GIST(affected_area);

CREATE TABLE IF NOT EXISTS infrastructure (
    id SERIAL PRIMARY KEY, source_id VARCHAR(100) NOT NULL UNIQUE,
    asset_type VARCHAR(50) NOT NULL, name VARCHAR(255), risk_level VARCHAR(50),
    estimated_arrival_time TIMESTAMP, exposure_duration_minutes INTEGER,
    priority VARCHAR(50), geometry GEOMETRY(GEOMETRY, 4326),
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_infrastructure_geom ON infrastructure USING GIST(geometry);
