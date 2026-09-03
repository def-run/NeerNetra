"""
NeerNetra — Data Seeder
=========================
Seeds the PostGIS database with historical flood events, landslide
susceptibility data, and infrastructure geometries.

Used for initial database population and demo preparation.
"""

import json
import os
from datetime import datetime
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


# ---------------------------------------------------------------------------
# Data file paths (relative to project root)
# ---------------------------------------------------------------------------
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data")

FLOOD_EVENTS_FILE = os.path.join(DATA_DIR, "flood_events", "kedarnath_historical_floods.json")
LANDSLIDE_FILE = os.path.join(DATA_DIR, "landslides", "kedarnath_landslide_susceptibility.json")
ROADS_FILE = os.path.join(DATA_DIR, "roads", "kedarnath_roads.geojson")
BRIDGES_FILE = os.path.join(DATA_DIR, "bridges", "kedarnath_bridges.geojson")


class DataSeeder:
    """
    Seeds PostGIS with initial data for the pilot region.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def seed_all(self) -> dict:
        """
        Run all seed operations.

        Returns:
            dict with counts of seeded records
        """
        results = {}

        results["flood_events"] = await self.seed_flood_events()
        results["landslide_data"] = await self.seed_landslide_data()
        results["roads"] = await self.seed_roads()
        results["bridges"] = await self.seed_bridges()

        return results

    async def seed_flood_events(self, filepath: Optional[str] = None) -> int:
        """
        Seed historical flood events into the flood_events table.

        Returns:
            Number of events inserted
        """
        filepath = filepath or FLOOD_EVENTS_FILE

        if not os.path.exists(filepath):
            print(f"Warning: Flood events file not found: {filepath}")
            return 0

        with open(filepath, "r") as f:
            data = json.load(f)

        events = data.get("events", [])
        count = 0

        for event in events:
            await self.session.execute(
                text("""
                    INSERT INTO flood_events (event_date, location_name, severity, description, source, geometry)
                    VALUES (:event_date, :location_name, :severity, :description, :source,
                            ST_SetSRID(ST_MakePoint(:lon, :lat), 4326))
                    ON CONFLICT DO NOTHING
                """),
                {
                    "event_date": event["event_date"],
                    "location_name": event["location_name"],
                    "severity": event["severity"],
                    "description": event.get("description", ""),
                    "source": event.get("source", ""),
                    "lat": event["lat"],
                    "lon": event["lon"],
                },
            )
            count += 1

        await self.session.commit()
        print(f"Seeded {count} flood events.")
        return count

    async def seed_landslide_data(self, filepath: Optional[str] = None) -> int:
        """
        Update locations table with landslide susceptibility data.

        Returns:
            Number of locations updated
        """
        filepath = filepath or LANDSLIDE_FILE

        if not os.path.exists(filepath):
            print(f"Warning: Landslide data file not found: {filepath}")
            return 0

        with open(filepath, "r") as f:
            data = json.load(f)

        locations = data.get("locations", [])
        count = 0

        for loc in locations:
            result = await self.session.execute(
                text("""
                    UPDATE locations
                    SET landslide_susceptibility = :susceptibility
                    WHERE name = :name
                """),
                {
                    "name": loc["name"],
                    "susceptibility": loc["landslide_susceptibility"],
                },
            )
            if result.rowcount > 0:
                count += 1

        await self.session.commit()
        print(f"Updated {count} locations with landslide susceptibility.")
        return count

    async def seed_roads(self, filepath: Optional[str] = None) -> int:
        """
        Seed road network into the infrastructure table.

        Returns:
            Number of road segments inserted
        """
        filepath = filepath or ROADS_FILE

        if not os.path.exists(filepath):
            print(f"Warning: Roads file not found: {filepath}")
            return 0

        with open(filepath, "r") as f:
            geojson = json.load(f)

        features = geojson.get("features", [])
        count = 0

        for feat in features:
            props = feat.get("properties", {})
            geom = json.dumps(feat.get("geometry", {}))

            await self.session.execute(
                text("""
                    INSERT INTO infrastructure (asset_type, name, risk_level, priority, geometry)
                    VALUES ('road', :name, :risk_level, :priority,
                            ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326))
                    ON CONFLICT DO NOTHING
                """),
                {
                    "name": props.get("name", "Unknown Road"),
                    "risk_level": props.get("flood_vulnerability", "unknown"),
                    "priority": props.get("importance", "unknown"),
                    "geom": geom,
                },
            )
            count += 1

        await self.session.commit()
        print(f"Seeded {count} road segments.")
        return count

    async def seed_bridges(self, filepath: Optional[str] = None) -> int:
        """
        Seed bridge locations into the infrastructure table.

        Returns:
            Number of bridges inserted
        """
        filepath = filepath or BRIDGES_FILE

        if not os.path.exists(filepath):
            print(f"Warning: Bridges file not found: {filepath}")
            return 0

        with open(filepath, "r") as f:
            geojson = json.load(f)

        features = geojson.get("features", [])
        count = 0

        for feat in features:
            props = feat.get("properties", {})
            geom = json.dumps(feat.get("geometry", {}))

            await self.session.execute(
                text("""
                    INSERT INTO infrastructure (asset_type, name, risk_level, priority, geometry)
                    VALUES ('bridge', :name, :risk_level, :priority,
                            ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326))
                    ON CONFLICT DO NOTHING
                """),
                {
                    "name": props.get("name", "Unknown Bridge"),
                    "risk_level": props.get("flood_vulnerability", "unknown"),
                    "priority": props.get("importance", "unknown"),
                    "geom": geom,
                },
            )
            count += 1

        await self.session.commit()
        print(f"Seeded {count} bridges.")
        return count
