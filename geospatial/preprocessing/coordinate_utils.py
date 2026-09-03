"""
NeerNetra — Coordinate & Timestamp Utilities
================================================
Standardizes all geospatial data to a common CRS (EPSG:4326)
and all timestamps to UTC.

This module ensures that data from different sources (Open-Meteo,
Copernicus DEM, NRSC, OpenStreetMap) can be spatially and temporally
aligned before being used by the ML pipeline.
"""

import numpy as np
from datetime import datetime, timezone
from typing import Union, Optional

try:
    from pyproj import Transformer, CRS
    HAS_PYPROJ = True
except ImportError:
    HAS_PYPROJ = False


# ---------------------------------------------------------------------------
# Standard Reference Systems
# ---------------------------------------------------------------------------
STANDARD_CRS = "EPSG:4326"  # WGS84 Lat/Lon
STANDARD_TZ = timezone.utc   # UTC timezone

# UTM Zone 44N — suitable for projected calculations in the Kedarnath area
PROJECTED_CRS = "EPSG:32644"


# ---------------------------------------------------------------------------
# Coordinate Utilities
# ---------------------------------------------------------------------------
def ensure_epsg4326(lat: float, lon: float, source_crs: str = "EPSG:4326") -> tuple:
    """
    Ensure coordinates are in EPSG:4326 (WGS84).

    If source_crs differs, transform them.

    Args:
        lat: Latitude or Y coordinate in source CRS
        lon: Longitude or X coordinate in source CRS
        source_crs: Source CRS string

    Returns:
        Tuple (lat, lon) in EPSG:4326
    """
    if source_crs == STANDARD_CRS:
        return (lat, lon)

    if not HAS_PYPROJ:
        raise ImportError("pyproj required for CRS transformation. Install: pip install pyproj")

    transformer = Transformer.from_crs(source_crs, STANDARD_CRS, always_xy=True)
    lon_out, lat_out = transformer.transform(lon, lat)
    return (lat_out, lon_out)


def to_projected(lat: float, lon: float, target_crs: str = PROJECTED_CRS) -> tuple:
    """
    Convert lat/lon (EPSG:4326) to a projected CRS for distance calculations.

    Default target: UTM Zone 44N (suitable for Uttarakhand).

    Returns:
        Tuple (x, y) in meters
    """
    if not HAS_PYPROJ:
        raise ImportError("pyproj required. Install: pip install pyproj")

    transformer = Transformer.from_crs(STANDARD_CRS, target_crs, always_xy=True)
    x, y = transformer.transform(lon, lat)
    return (x, y)


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points (Haversine formula).

    Args:
        lat1, lon1: First point coordinates (degrees)
        lat2, lon2: Second point coordinates (degrees)

    Returns:
        Distance in kilometers
    """
    R = 6371.0  # Earth radius in km

    lat1_r, lon1_r = np.radians(lat1), np.radians(lon1)
    lat2_r, lon2_r = np.radians(lat2), np.radians(lon2)

    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r

    a = np.sin(dlat / 2) ** 2 + np.cos(lat1_r) * np.cos(lat2_r) * np.sin(dlon / 2) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

    return round(R * c, 3)


def is_within_bounds(
    lat: float,
    lon: float,
    bounds: dict,
) -> bool:
    """
    Check if a coordinate is within a bounding box.

    Args:
        lat, lon: Coordinates
        bounds: Dict with 'north', 'south', 'east', 'west' keys

    Returns:
        True if within bounds
    """
    return (
        bounds["south"] <= lat <= bounds["north"]
        and bounds["west"] <= lon <= bounds["east"]
    )


# Pilot region bounds
PILOT_BOUNDS = {
    "north": 30.85,
    "south": 30.20,
    "east": 79.20,
    "west": 78.90,
}


def is_in_pilot_region(lat: float, lon: float) -> bool:
    """Check if coordinates are within the Kedarnath pilot region."""
    return is_within_bounds(lat, lon, PILOT_BOUNDS)


# ---------------------------------------------------------------------------
# Timestamp Utilities
# ---------------------------------------------------------------------------
def to_utc(dt: Union[str, datetime]) -> datetime:
    """
    Convert a datetime or ISO string to UTC.

    Args:
        dt: datetime object or ISO format string

    Returns:
        Timezone-aware datetime in UTC
    """
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))

    if dt.tzinfo is None:
        # Assume UTC if no timezone info
        dt = dt.replace(tzinfo=STANDARD_TZ)

    return dt.astimezone(STANDARD_TZ)


def utc_now() -> datetime:
    """Get current time in UTC."""
    return datetime.now(STANDARD_TZ)


def format_iso(dt: datetime) -> str:
    """Format datetime as ISO 8601 string."""
    return dt.isoformat()


def align_timestamp_to_hour(dt: Union[str, datetime]) -> datetime:
    """
    Round a timestamp down to the nearest hour.

    Useful for aligning data from different sources that report
    at different sub-hourly intervals.
    """
    dt = to_utc(dt) if isinstance(dt, str) else dt
    return dt.replace(minute=0, second=0, microsecond=0)
