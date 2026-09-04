"""Explicit, repeatable PostgreSQL/PostGIS schema and static-data bootstrap."""

import argparse
import asyncio
from pathlib import Path

import asyncpg
from sqlalchemy import text

from backend.config.locations import PILOT_LOCATIONS
from backend.database.connection import async_session
from backend.services.ingestion.data_seeder import DataSeeder


async def bootstrap() -> dict:
    schema_path = Path(__file__).with_name("schema.sql")
    statements = [part.strip() for part in schema_path.read_text(encoding="utf-8").split(";") if part.strip()]
    async with async_session() as session:
        for statement in statements:
            await session.execute(text(statement))
        # Upgrade databases created by the original schema before using
        # conflict-targeted upserts.
        migrations = [
            "DELETE FROM locations a USING locations b WHERE a.name = b.name AND a.id > b.id",
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_locations_name ON locations (name)",
            "ALTER TABLE flood_events ADD COLUMN IF NOT EXISTS source_id VARCHAR(100)",
            "ALTER TABLE flood_events ADD COLUMN IF NOT EXISTS end_date TIMESTAMP",
            "ALTER TABLE flood_events ADD COLUMN IF NOT EXISTS flood_type VARCHAR(100)",
            "ALTER TABLE flood_events ADD COLUMN IF NOT EXISTS estimated_rainfall_24h_mm DOUBLE PRECISION",
            "ALTER TABLE flood_events ADD COLUMN IF NOT EXISTS estimated_rainfall_72h_mm DOUBLE PRECISION",
            "ALTER TABLE flood_events ADD COLUMN IF NOT EXISTS deaths INTEGER",
            "ALTER TABLE flood_events ADD COLUMN IF NOT EXISTS affected_locations JSONB",
            "UPDATE flood_events SET source_id = 'legacy-' || id::text WHERE source_id IS NULL",
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_flood_events_source_id ON flood_events (source_id)",
            "ALTER TABLE infrastructure ADD COLUMN IF NOT EXISTS source_id VARCHAR(100)",
            "UPDATE infrastructure SET source_id = asset_type || chr(58) || 'legacy-' || id::text WHERE source_id IS NULL",
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_infrastructure_source_id ON infrastructure (source_id)",
            "ALTER TABLE predictions ADD COLUMN IF NOT EXISTS drivers JSONB",
            "ALTER TABLE propagation_results ADD COLUMN IF NOT EXISTS result_data JSONB NOT NULL DEFAULT '{}'::jsonb",
            "ALTER TABLE propagation_results ADD COLUMN IF NOT EXISTS arrival_time_grid JSONB",
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_weather_observation ON weather_observations (location_id, timestamp, source)",
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_rainfall_feature ON rainfall_features (location_id, timestamp)",
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_prediction_run ON predictions (location_id, timestamp, model_type)",
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_propagation_step ON propagation_results (prediction_id, time_step_minutes)",
        ]
        for migration in migrations:
            await session.execute(text(migration))
        for loc in PILOT_LOCATIONS:
            await session.execute(
                text(
                    """INSERT INTO locations (name, latitude, longitude, elevation, geometry)
                    VALUES (:name, :lat, :lon, :elev, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326))
                    ON CONFLICT (name) DO UPDATE SET latitude=EXCLUDED.latitude,
                    longitude=EXCLUDED.longitude, elevation=EXCLUDED.elevation,
                    geometry=EXCLUDED.geometry"""
                ),
                loc,
            )
        await session.commit()
        result = await DataSeeder(session).seed_all()
        await session.commit()
        return {"locations": len(PILOT_LOCATIONS), **result}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize NeerNetra PostgreSQL/PostGIS")
    parser.parse_args()
    try:
        print(asyncio.run(bootstrap()))
    except asyncpg.InvalidPasswordError as exc:
        raise SystemExit(
            "PostgreSQL rejected DATABASE_URL credentials. "
            "Update .env DATABASE_URL to match POSTGRES_USER/POSTGRES_PASSWORD, "
            "or start the project database with `docker compose up -d db`."
        ) from exc
    except (asyncpg.InvalidCatalogNameError, asyncpg.ConnectionDoesNotExistError) as exc:
        raise SystemExit(
            "Could not connect to PostgreSQL. Confirm the database is running and "
            "DATABASE_URL points to the correct host, port, and database."
        ) from exc
