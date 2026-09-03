"""
NeerNetra — ML Feature Engineering Module
============================================
Build the feature set for flood prediction (Section 6.3).

Environmental / Weather Features:
    rain_1h, rain_3h, rain_6h, rain_12h, rain_24h, rain_72h,
    forecast_rain_3h, forecast_rain_6h,
    rainfall_intensity, rainfall_acceleration,
    temperature, humidity

Terrain Features:
    elevation, slope, aspect, terrain_ruggedness,
    drainage-related indicators, distance_to_waterbody

Flood History Features:
    historical_flood_frequency, historical_event_severity,
    historical_flood_susceptibility

Cascade / Infrastructure Features:
    landslide_susceptibility, blockage_indicator,
    distance_to_road, road_exposure_indicator, bridge_exposure_indicator
"""

FEATURE_COLUMNS = [
    # Environmental / Weather
    "rain_1h", "rain_3h", "rain_6h", "rain_12h", "rain_24h", "rain_72h",
    "forecast_rain_3h", "forecast_rain_6h",
    "rainfall_intensity", "rainfall_acceleration",
    "temperature", "humidity",
    # Terrain
    "elevation", "slope", "aspect", "terrain_ruggedness",
    "distance_to_waterbody",
    # Flood History
    "historical_flood_frequency", "historical_event_severity",
    "historical_flood_susceptibility",
    # Cascade / Infrastructure
    "landslide_susceptibility", "blockage_indicator",
    "distance_to_road", "road_exposure_indicator", "bridge_exposure_indicator",
]

TARGET_COLUMN = "flood_event"  # 0 = No flood, 1 = Flood
