"""
NeerNetra — Synthetic DEM Generator
=====================================
Generates a realistic synthetic Digital Elevation Model (DEM) for the
Kedarnath / Mandakini Valley pilot region.

This is used when real Copernicus DEM data is not available, providing
a terrain surface that approximates the actual topography for prototype
development and demonstration.

The Kedarnath region terrain characteristics:
- Elevation range: ~600m (Rudraprayag) to ~6,900m (peaks near Kedarnath)
- Steep river valley (Mandakini) with high-gradient slopes
- Ridge-valley pattern typical of Lesser/Greater Himalaya

Output: GeoTIFF raster compatible with Rasterio.
"""

import numpy as np

try:
    import rasterio
    from rasterio.transform import from_bounds
    from rasterio.crs import CRS
    HAS_RASTERIO = True
except ImportError:
    HAS_RASTERIO = False


# ---------------------------------------------------------------------------
# Pilot Region Bounds
# ---------------------------------------------------------------------------
BOUNDS = {
    "west": 78.90,
    "east": 79.20,
    "south": 30.20,
    "north": 30.85,
}

# Monitored locations with real elevations
KNOWN_POINTS = [
    {"name": "Kedarnath",    "lat": 30.7346, "lon": 79.0669, "elev": 3583},
    {"name": "Gaurikund",    "lat": 30.6560, "lon": 79.0900, "elev": 1982},
    {"name": "Sonprayag",    "lat": 30.6280, "lon": 79.0700, "elev": 1829},
    {"name": "Rampur",       "lat": 30.6350, "lon": 79.0520, "elev": 1800},
    {"name": "Sitapur",      "lat": 30.6100, "lon": 79.0400, "elev": 1600},
    {"name": "Agastmuni",    "lat": 30.5260, "lon": 79.0260, "elev": 1000},
    {"name": "Rudraprayag",  "lat": 30.2840, "lon": 78.9800, "elev":  610},
    {"name": "Guptkashi",    "lat": 30.5300, "lon": 79.0700, "elev": 1319},
    {"name": "Phata",        "lat": 30.5700, "lon": 79.0600, "elev": 1524},
    {"name": "Kalimath",     "lat": 30.5500, "lon": 79.0400, "elev": 1463},
]


def generate_synthetic_dem(
    output_path: str,
    resolution_deg: float = 0.001,  # ~90m at this latitude
) -> str:
    """
    Generate a synthetic DEM GeoTIFF for the pilot region.

    Uses inverse-distance weighting from known elevation points
    plus terrain noise to create a realistic surface.

    Args:
        output_path: Path to write the GeoTIFF file
        resolution_deg: Grid resolution in degrees (default ~90m)

    Returns:
        Path to the generated file
    """
    if not HAS_RASTERIO:
        raise ImportError(
            "rasterio is required for DEM generation. "
            "Install with: pip install rasterio"
        )

    # Build coordinate grid
    lons = np.arange(BOUNDS["west"], BOUNDS["east"], resolution_deg)
    lats = np.arange(BOUNDS["north"], BOUNDS["south"], -resolution_deg)  # N→S
    n_rows = len(lats)
    n_cols = len(lons)

    print(f"Generating synthetic DEM: {n_rows} x {n_cols} ({n_rows * n_cols:,} cells)")

    # Create meshgrid
    lon_grid, lat_grid = np.meshgrid(lons, lats)

    # ----- Inverse Distance Weighting from known points -----
    elevation = np.zeros_like(lon_grid)
    weights_total = np.zeros_like(lon_grid)

    for pt in KNOWN_POINTS:
        dist = np.sqrt(
            ((lon_grid - pt["lon"]) ** 2) +
            ((lat_grid - pt["lat"]) ** 2)
        )
        # Avoid division by zero
        dist = np.maximum(dist, 1e-8)
        # IDW with power = 2
        w = 1.0 / (dist ** 2)
        elevation += w * pt["elev"]
        weights_total += w

    elevation = elevation / weights_total

    # ----- Add realistic terrain features -----
    # 1. Latitude-dependent base elevation (higher in north)
    lat_factor = (lat_grid - BOUNDS["south"]) / (BOUNDS["north"] - BOUNDS["south"])
    elevation += lat_factor * 400  # ~400m additional in the north

    # 2. Valley along the Mandakini river corridor (~79.05°E)
    river_lon = 79.05
    valley_dist = np.abs(lon_grid - river_lon)
    valley_depth = 200 * np.exp(-valley_dist / 0.03)  # Gaussian valley
    elevation -= valley_depth

    # 3. Ridge features on both sides of the valley
    for ridge_lon in [78.95, 79.15]:
        ridge_dist = np.abs(lon_grid - ridge_lon)
        ridge_height = 300 * np.exp(-ridge_dist / 0.04)
        elevation += ridge_height

    # 4. Medium-scale terrain roughness
    np.random.seed(42)
    roughness = np.random.normal(0, 50, elevation.shape)
    # Smooth the noise a bit with a simple box filter
    from scipy.ndimage import uniform_filter
    roughness = uniform_filter(roughness, size=5)
    elevation += roughness

    # 5. Ensure minimum elevation and clamp
    elevation = np.maximum(elevation, 400)  # Minimum 400m (valley floor)
    elevation = np.minimum(elevation, 5500)  # Max 5500m (peaks)
    elevation = elevation.astype(np.float32)

    # ----- Write GeoTIFF -----
    transform = from_bounds(
        BOUNDS["west"], BOUNDS["south"],
        BOUNDS["east"], BOUNDS["north"],
        n_cols, n_rows,
    )

    with rasterio.open(
        output_path,
        "w",
        driver="GTiff",
        height=n_rows,
        width=n_cols,
        count=1,
        dtype=np.float32,
        crs=CRS.from_epsg(4326),
        transform=transform,
        nodata=-9999,
    ) as dst:
        dst.write(elevation, 1)
        dst.set_band_description(1, "Elevation (meters)")

    print(f"Synthetic DEM written to: {output_path}")
    print(f"  Elevation range: {elevation.min():.0f}m – {elevation.max():.0f}m")
    print(f"  Grid: {n_rows} × {n_cols} cells")
    print(f"  Resolution: ~{resolution_deg * 111000:.0f}m")

    return output_path


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import os
    output = os.path.join(
        os.path.dirname(__file__),
        "..", "..", "data", "dem", "kedarnath_synthetic_dem.tif"
    )
    output = os.path.abspath(output)
    generate_synthetic_dem(output)
