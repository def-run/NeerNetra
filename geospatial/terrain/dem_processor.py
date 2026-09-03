"""
NeerNetra — DEM Processor
===========================
Processes Digital Elevation Model (DEM) rasters using Rasterio.

Reads GeoTIFF DEM files and provides methods for:
- Loading and validating DEM data
- Extracting elevation at specific coordinates
- Computing basic statistics
- Preparing DEM for terrain feature extraction

Works with both real Copernicus DEM and synthetic DEMs.
"""

import numpy as np
from typing import Optional, Tuple

try:
    import rasterio
    from rasterio.transform import rowcol
    from rasterio.warp import transform as warp_transform
    HAS_RASTERIO = True
except ImportError:
    HAS_RASTERIO = False


class DEMProcessor:
    """
    Processes DEM raster data for terrain analysis.
    """

    def __init__(self, dem_path: str):
        """
        Initialize with path to a DEM GeoTIFF file.

        Args:
            dem_path: Path to the DEM GeoTIFF
        """
        if not HAS_RASTERIO:
            raise ImportError("rasterio is required. Install: pip install rasterio")

        self.dem_path = dem_path
        self._elevation = None
        self._transform = None
        self._crs = None
        self._bounds = None
        self._shape = None
        self._nodata = None

    def load(self) -> "DEMProcessor":
        """Load the DEM into memory."""
        with rasterio.open(self.dem_path) as src:
            self._elevation = src.read(1).astype(np.float32)
            self._transform = src.transform
            self._crs = src.crs
            self._bounds = src.bounds
            self._shape = src.shape
            self._nodata = src.nodata

        # Replace nodata with NaN
        if self._nodata is not None:
            self._elevation[self._elevation == self._nodata] = np.nan

        return self

    @property
    def elevation(self) -> np.ndarray:
        """Get elevation array (rows x cols)."""
        if self._elevation is None:
            self.load()
        return self._elevation

    @property
    def shape(self) -> Tuple[int, int]:
        """Get (rows, cols) shape."""
        if self._shape is None:
            self.load()
        return self._shape

    @property
    def bounds(self):
        """Get spatial bounds."""
        if self._bounds is None:
            self.load()
        return self._bounds

    @property
    def resolution_m(self) -> float:
        """Approximate resolution in meters."""
        if self._transform is None:
            self.load()
        # At ~30°N latitude, 1° ≈ 111km
        return abs(self._transform.a) * 111_000

    def get_elevation_at(self, lat: float, lon: float) -> Optional[float]:
        """
        Get elevation at a specific lat/lon coordinate.

        Args:
            lat: Latitude (WGS84)
            lon: Longitude (WGS84)

        Returns:
            Elevation in meters, or None if out of bounds
        """
        if self._elevation is None:
            self.load()

        try:
            row, col = rowcol(self._transform, lon, lat)
            if 0 <= row < self._shape[0] and 0 <= col < self._shape[1]:
                val = float(self._elevation[row, col])
                return val if not np.isnan(val) else None
            return None
        except Exception:
            return None

    def get_elevation_grid(
        self,
        lat_min: float,
        lat_max: float,
        lon_min: float,
        lon_max: float,
    ) -> Tuple[np.ndarray, dict]:
        """
        Extract a subgrid of elevation data.

        Returns:
            Tuple of (elevation_array, metadata_dict)
        """
        if self._elevation is None:
            self.load()

        # Convert corners to pixel coordinates
        row_max, col_min = rowcol(self._transform, lon_min, lat_min)
        row_min, col_max = rowcol(self._transform, lon_max, lat_max)

        # Clamp to valid range
        row_min = max(0, min(row_min, self._shape[0] - 1))
        row_max = max(0, min(row_max, self._shape[0] - 1))
        col_min = max(0, min(col_min, self._shape[1] - 1))
        col_max = max(0, min(col_max, self._shape[1] - 1))

        subgrid = self._elevation[row_min:row_max + 1, col_min:col_max + 1]

        metadata = {
            "shape": subgrid.shape,
            "lat_range": (lat_min, lat_max),
            "lon_range": (lon_min, lon_max),
            "elevation_min": float(np.nanmin(subgrid)) if subgrid.size else None,
            "elevation_max": float(np.nanmax(subgrid)) if subgrid.size else None,
        }

        return subgrid, metadata

    def get_statistics(self) -> dict:
        """Get basic elevation statistics."""
        elev = self.elevation
        valid = elev[~np.isnan(elev)]

        return {
            "min_elevation_m": float(np.min(valid)),
            "max_elevation_m": float(np.max(valid)),
            "mean_elevation_m": float(np.mean(valid)),
            "std_elevation_m": float(np.std(valid)),
            "total_cells": int(elev.size),
            "valid_cells": int(valid.size),
            "shape": self.shape,
            "resolution_m": round(self.resolution_m, 1),
            "crs": str(self._crs),
        }
