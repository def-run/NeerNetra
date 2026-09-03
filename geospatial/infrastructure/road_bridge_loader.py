"""
NeerNetra — Road & Bridge Loader
===================================
Loads road and bridge GeoJSON data into PostGIS and provides
GeoPandas-based spatial operations for infrastructure analysis.
"""

import json
import os
from typing import Optional

try:
    import geopandas as gpd
    from shapely.geometry import shape
    HAS_GEOPANDAS = True
except ImportError:
    HAS_GEOPANDAS = False


# Default data paths (relative to project root)
DEFAULT_ROADS_PATH = os.path.join("data", "roads", "kedarnath_roads.geojson")
DEFAULT_BRIDGES_PATH = os.path.join("data", "bridges", "kedarnath_bridges.geojson")


class RoadBridgeLoader:
    """
    Loads and manages road/bridge infrastructure data.
    """

    def __init__(
        self,
        roads_path: Optional[str] = None,
        bridges_path: Optional[str] = None,
    ):
        self.roads_path = roads_path or DEFAULT_ROADS_PATH
        self.bridges_path = bridges_path or DEFAULT_BRIDGES_PATH
        self._roads_gdf = None
        self._bridges_gdf = None

    def load_roads(self) -> "gpd.GeoDataFrame":
        """Load road network from GeoJSON into a GeoDataFrame."""
        if not HAS_GEOPANDAS:
            raise ImportError("geopandas required. Install: pip install geopandas")

        self._roads_gdf = gpd.read_file(self.roads_path)
        self._roads_gdf = self._roads_gdf.set_crs("EPSG:4326", allow_override=True)
        return self._roads_gdf

    def load_bridges(self) -> "gpd.GeoDataFrame":
        """Load bridge locations from GeoJSON into a GeoDataFrame."""
        if not HAS_GEOPANDAS:
            raise ImportError("geopandas required. Install: pip install geopandas")

        self._bridges_gdf = gpd.read_file(self.bridges_path)
        self._bridges_gdf = self._bridges_gdf.set_crs("EPSG:4326", allow_override=True)
        return self._bridges_gdf

    def load_all(self) -> dict:
        """Load both roads and bridges."""
        return {
            "roads": self.load_roads(),
            "bridges": self.load_bridges(),
        }

    @property
    def roads(self) -> "gpd.GeoDataFrame":
        if self._roads_gdf is None:
            self.load_roads()
        return self._roads_gdf

    @property
    def bridges(self) -> "gpd.GeoDataFrame":
        if self._bridges_gdf is None:
            self.load_bridges()
        return self._bridges_gdf

    def get_roads_near(
        self,
        lat: float,
        lon: float,
        buffer_km: float = 5.0,
    ) -> "gpd.GeoDataFrame":
        """
        Get road segments within a buffer distance of a point.

        Args:
            lat: Latitude
            lon: Longitude
            buffer_km: Search radius in km

        Returns:
            GeoDataFrame of nearby road segments
        """
        from shapely.geometry import Point

        point = Point(lon, lat)
        # Approximate buffer in degrees (~1 degree ≈ 111 km)
        buffer_deg = buffer_km / 111.0
        buffered = point.buffer(buffer_deg)

        roads = self.roads
        nearby = roads[roads.intersects(buffered)]
        return nearby

    def get_bridges_near(
        self,
        lat: float,
        lon: float,
        buffer_km: float = 5.0,
    ) -> "gpd.GeoDataFrame":
        """Get bridges within a buffer distance of a point."""
        from shapely.geometry import Point

        point = Point(lon, lat)
        buffer_deg = buffer_km / 111.0
        buffered = point.buffer(buffer_deg)

        bridges = self.bridges
        nearby = bridges[bridges.within(buffered)]
        return nearby

    def get_road_statistics(self) -> dict:
        """Get summary statistics about the road network."""
        roads = self.roads
        return {
            "total_segments": len(roads),
            "road_types": roads["road_type"].value_counts().to_dict()
            if "road_type" in roads.columns
            else {},
            "vulnerability_breakdown": roads["flood_vulnerability"].value_counts().to_dict()
            if "flood_vulnerability" in roads.columns
            else {},
            "total_length_km": round(
                float(roads.to_crs("EPSG:32644").length.sum() / 1000), 2
            )
            if len(roads) > 0
            else 0,
        }

    def get_bridge_statistics(self) -> dict:
        """Get summary statistics about bridges."""
        bridges = self.bridges
        return {
            "total_bridges": len(bridges),
            "bridge_types": bridges["bridge_type"].value_counts().to_dict()
            if "bridge_type" in bridges.columns
            else {},
            "vulnerability_breakdown": bridges["flood_vulnerability"].value_counts().to_dict()
            if "flood_vulnerability" in bridges.columns
            else {},
        }

    def to_postgis_sql(self) -> str:
        """
        Generate SQL INSERT statements for loading infrastructure into PostGIS.

        Returns:
            SQL string for inserting roads and bridges
        """
        sql_parts = ["-- Auto-generated infrastructure INSERT statements\n"]

        # Roads
        for _, row in self.roads.iterrows():
            geom_wkt = row.geometry.wkt
            name = row.get("name", "Unknown").replace("'", "''")
            asset_type = "road"
            vulnerability = row.get("flood_vulnerability", "unknown")
            importance = row.get("importance", "unknown")

            sql_parts.append(
                f"INSERT INTO infrastructure (asset_type, name, risk_level, priority, geometry) "
                f"VALUES ('{asset_type}', '{name}', '{vulnerability}', '{importance}', "
                f"ST_GeomFromText('{geom_wkt}', 4326));"
            )

        # Bridges
        for _, row in self.bridges.iterrows():
            geom_wkt = row.geometry.wkt
            name = row.get("name", "Unknown").replace("'", "''")
            asset_type = "bridge"
            vulnerability = row.get("flood_vulnerability", "unknown")
            importance = row.get("importance", "unknown")

            sql_parts.append(
                f"INSERT INTO infrastructure (asset_type, name, risk_level, priority, geometry) "
                f"VALUES ('{asset_type}', '{name}', '{vulnerability}', '{importance}', "
                f"ST_GeomFromText('{geom_wkt}', 4326));"
            )

        return "\n".join(sql_parts)
