"""
NeerNetra — Terrain Feature Extractor
========================================
Derives terrain features from DEM rasters for flood prediction.

Features extracted (Section 6.3 — Terrain Features):
    - elevation
    - slope (degrees)
    - aspect (degrees, 0=N, 90=E, 180=S, 270=W)
    - terrain_ruggedness (TRI)
    - drainage-related indicators
    - distance_to_waterbody (approximate)

These features are static per location and computed once during data preparation.
"""

import numpy as np
from typing import Optional

try:
    import rasterio
    from rasterio.transform import rowcol, xy
    HAS_RASTERIO = True
except ImportError:
    HAS_RASTERIO = False

from geospatial.terrain.dem_processor import DEMProcessor


class TerrainFeatureExtractor:
    """
    Extracts terrain-derived features from a DEM.
    """

    def __init__(self, dem_processor: DEMProcessor):
        """
        Initialize with a loaded DEMProcessor.

        Args:
            dem_processor: An initialized DEMProcessor instance
        """
        self.dem = dem_processor
        self._slope = None
        self._aspect = None
        self._tri = None

    def extract_all_features(self, lat: float, lon: float) -> dict:
        """
        Extract all terrain features for a specific coordinate.

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            dict with elevation, slope, aspect, terrain_ruggedness, etc.
        """
        elevation = self.dem.get_elevation_at(lat, lon)

        if elevation is None:
            return self._empty_features()

        # Ensure derived grids are computed
        self._ensure_computed()

        # Get pixel position
        row, col = rowcol(self.dem._transform, lon, lat)

        features = {
            "elevation": round(elevation, 1),
            "slope": self._get_value(self._slope, row, col),
            "aspect": self._get_value(self._aspect, row, col),
            "terrain_ruggedness": self._get_value(self._tri, row, col),
            "drainage_indicator": self._compute_drainage_indicator(row, col),
            "distance_to_waterbody": self._estimate_distance_to_waterbody(lat, lon),
        }

        return features

    def compute_slope_grid(self) -> np.ndarray:
        """
        Compute slope in degrees from the DEM.

        Uses a 3x3 gradient calculation (Horn's method).
        """
        elev = self.dem.elevation
        cell_size = self.dem.resolution_m

        # Compute gradients using numpy
        # Pad edges to handle boundaries
        padded = np.pad(elev, 1, mode="edge")

        # Horizontal gradient (dz/dx)
        dzdx = (
            (padded[:-2, 2:] + 2 * padded[1:-1, 2:] + padded[2:, 2:]) -
            (padded[:-2, :-2] + 2 * padded[1:-1, :-2] + padded[2:, :-2])
        ) / (8 * cell_size)

        # Vertical gradient (dz/dy)
        dzdy = (
            (padded[2:, :-2] + 2 * padded[2:, 1:-1] + padded[2:, 2:]) -
            (padded[:-2, :-2] + 2 * padded[:-2, 1:-1] + padded[:-2, 2:])
        ) / (8 * cell_size)

        # Slope in degrees
        slope = np.degrees(np.arctan(np.sqrt(dzdx**2 + dzdy**2)))

        # Handle NaN
        slope = np.where(np.isnan(elev), np.nan, slope)

        self._slope = slope
        return slope

    def compute_aspect_grid(self) -> np.ndarray:
        """
        Compute aspect (slope direction) in degrees from the DEM.

        0° = North, 90° = East, 180° = South, 270° = West
        """
        elev = self.dem.elevation
        cell_size = self.dem.resolution_m

        padded = np.pad(elev, 1, mode="edge")

        dzdx = (
            (padded[:-2, 2:] + 2 * padded[1:-1, 2:] + padded[2:, 2:]) -
            (padded[:-2, :-2] + 2 * padded[1:-1, :-2] + padded[2:, :-2])
        ) / (8 * cell_size)

        dzdy = (
            (padded[2:, :-2] + 2 * padded[2:, 1:-1] + padded[2:, 2:]) -
            (padded[:-2, :-2] + 2 * padded[:-2, 1:-1] + padded[:-2, 2:])
        ) / (8 * cell_size)

        # Aspect in degrees from north
        aspect = np.degrees(np.arctan2(-dzdx, dzdy))
        aspect = np.where(aspect < 0, aspect + 360, aspect)
        aspect = np.where(np.isnan(elev), np.nan, aspect)

        self._aspect = aspect
        return aspect

    def compute_tri_grid(self) -> np.ndarray:
        """
        Compute Terrain Ruggedness Index (TRI).

        TRI = mean of absolute elevation differences between a cell
        and its 8 neighbors. Higher values = rougher terrain.
        """
        elev = self.dem.elevation
        padded = np.pad(elev, 1, mode="edge")

        tri = np.zeros_like(elev)
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue
                neighbor = padded[1 + dr:padded.shape[0] - 1 + dr,
                                  1 + dc:padded.shape[1] - 1 + dc]
                tri += np.abs(elev - neighbor)

        tri = tri / 8.0  # Average over 8 neighbors
        tri = np.where(np.isnan(elev), np.nan, tri)

        self._tri = tri
        return tri

    def extract_features_for_locations(
        self, locations: list[dict]
    ) -> list[dict]:
        """
        Extract terrain features for multiple locations.

        Args:
            locations: List of dicts with 'lat', 'lon', 'name' keys

        Returns:
            List of feature dicts, one per location
        """
        self._ensure_computed()

        results = []
        for loc in locations:
            features = self.extract_all_features(loc["lat"], loc["lon"])
            features["name"] = loc.get("name", "Unknown")
            features["lat"] = loc["lat"]
            features["lon"] = loc["lon"]
            results.append(features)

        return results

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------
    def _ensure_computed(self):
        """Compute derived grids if not yet done."""
        if self._slope is None:
            self.compute_slope_grid()
        if self._aspect is None:
            self.compute_aspect_grid()
        if self._tri is None:
            self.compute_tri_grid()

    @staticmethod
    def _get_value(grid: np.ndarray, row: int, col: int) -> Optional[float]:
        """Safely get a value from a 2D grid."""
        if grid is None:
            return None
        if 0 <= row < grid.shape[0] and 0 <= col < grid.shape[1]:
            val = float(grid[row, col])
            return round(val, 2) if not np.isnan(val) else None
        return None

    def _compute_drainage_indicator(self, row: int, col: int) -> float:
        """
        Simplified drainage indicator based on local topography.

        Lower elevation relative to neighbors = higher drainage accumulation.
        Returns value 0.0 (ridge) to 1.0 (valley/drainage).
        """
        elev = self.dem.elevation
        if row < 1 or row >= elev.shape[0] - 1 or col < 1 or col >= elev.shape[1] - 1:
            return 0.5

        center = elev[row, col]
        neighbors = elev[row - 1:row + 2, col - 1:col + 2].flatten()
        neighbors = neighbors[~np.isnan(neighbors)]

        if len(neighbors) == 0 or np.isnan(center):
            return 0.5

        # Count how many neighbors are higher (water flows toward this cell)
        higher_count = np.sum(neighbors > center)
        indicator = higher_count / len(neighbors)

        return round(indicator, 2)

    @staticmethod
    def _estimate_distance_to_waterbody(lat: float, lon: float) -> float:
        """
        Estimate distance to nearest major waterbody/river.

        Uses a simplified representation of the Mandakini river
        running approximately along longitude 79.05-79.07°E.

        Returns distance in km.
        """
        # Simplified Mandakini river path (lon, lat waypoints)
        river_points = [
            (78.980, 30.284),  # Rudraprayag
            (79.026, 30.526),  # Agastmuni
            (79.060, 30.570),  # Phata
            (79.070, 30.628),  # Sonprayag
            (79.090, 30.656),  # Gaurikund
            (79.067, 30.735),  # Kedarnath
        ]

        min_dist = float("inf")
        for r_lon, r_lat in river_points:
            # Approximate distance in km (haversine simplified)
            dlat = (lat - r_lat) * 111.0
            dlon = (lon - r_lon) * 111.0 * np.cos(np.radians(lat))
            dist = np.sqrt(dlat**2 + dlon**2)
            min_dist = min(min_dist, dist)

        return round(min_dist, 2)

    @staticmethod
    def _empty_features() -> dict:
        """Return None-filled features."""
        return {
            "elevation": None,
            "slope": None,
            "aspect": None,
            "terrain_ruggedness": None,
            "drainage_indicator": None,
            "distance_to_waterbody": None,
        }
