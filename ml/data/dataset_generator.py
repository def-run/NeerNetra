"""
NeerNetra — Synthetic Training Dataset Generator
====================================================
Generates a realistic labeled dataset for flood prediction model training.

Since we don't have a massive historical labeled dataset, this module
creates synthetic observations that follow realistic patterns observed
in the Kedarnath / Mandakini Valley region:

- Flood events correlate with high rainfall, steep terrain, high susceptibility
- Non-flood conditions are the majority class (imbalanced, like reality)
- Feature distributions are modeled after real-world ranges

The dataset includes all features from Section 6.3:
  Environmental: rain_1h..rain_72h, forecast_rain_3h/6h, intensity, acceleration, temp, humidity
  Terrain: elevation, slope, aspect, terrain_ruggedness, distance_to_waterbody
  Historical: historical_flood_frequency, historical_event_severity, historical_flood_susceptibility
  Cascade: landslide_susceptibility, blockage_indicator, distance_to_road, road_exposure, bridge_exposure

Target: flood_event (0 = no flood, 1 = flood)
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional


# ---------------------------------------------------------------------------
# Pilot Location Profiles (based on real data from Phase 2)
# ---------------------------------------------------------------------------
LOCATION_PROFILES = [
    {"name": "Kedarnath",   "elev": 3583, "slope": 35, "aspect": 180, "tri": 120, "dist_water": 0.3,
     "flood_freq": 3, "flood_suscep": 0.85, "landslide_suscep": 0.85, "dist_road": 0.5},
    {"name": "Gaurikund",   "elev": 1982, "slope": 28, "aspect": 200, "tri": 85,  "dist_water": 0.1,
     "flood_freq": 5, "flood_suscep": 0.78, "landslide_suscep": 0.78, "dist_road": 0.1},
    {"name": "Sonprayag",   "elev": 1829, "slope": 22, "aspect": 190, "tri": 70,  "dist_water": 0.1,
     "flood_freq": 4, "flood_suscep": 0.72, "landslide_suscep": 0.72, "dist_road": 0.1},
    {"name": "Rampur",      "elev": 1800, "slope": 18, "aspect": 210, "tri": 55,  "dist_water": 0.5,
     "flood_freq": 2, "flood_suscep": 0.55, "landslide_suscep": 0.65, "dist_road": 0.2},
    {"name": "Sitapur",     "elev": 1600, "slope": 15, "aspect": 220, "tri": 45,  "dist_water": 0.4,
     "flood_freq": 1, "flood_suscep": 0.45, "landslide_suscep": 0.55, "dist_road": 0.3},
    {"name": "Agastmuni",   "elev": 1000, "slope": 12, "aspect": 160, "tri": 35,  "dist_water": 0.2,
     "flood_freq": 2, "flood_suscep": 0.50, "landslide_suscep": 0.45, "dist_road": 0.1},
    {"name": "Rudraprayag", "elev":  610, "slope":  8, "aspect": 170, "tri": 25,  "dist_water": 0.1,
     "flood_freq": 3, "flood_suscep": 0.60, "landslide_suscep": 0.52, "dist_road": 0.05},
    {"name": "Guptkashi",   "elev": 1319, "slope": 20, "aspect": 240, "tri": 60,  "dist_water": 0.3,
     "flood_freq": 2, "flood_suscep": 0.55, "landslide_suscep": 0.60, "dist_road": 0.2},
    {"name": "Phata",       "elev": 1524, "slope": 25, "aspect": 195, "tri": 75,  "dist_water": 0.2,
     "flood_freq": 3, "flood_suscep": 0.65, "landslide_suscep": 0.68, "dist_road": 0.1},
    {"name": "Kalimath",    "elev": 1463, "slope": 18, "aspect": 230, "tri": 50,  "dist_water": 0.6,
     "flood_freq": 2, "flood_suscep": 0.50, "landslide_suscep": 0.62, "dist_road": 0.4},
]


def generate_dataset(
    n_samples: int = 5000,
    flood_ratio: float = 0.15,
    seed: int = 42,
    start_date: str = "2018-01-01",
    end_date: str = "2026-06-30",
) -> pd.DataFrame:
    """
    Generate a realistic synthetic training dataset.

    Args:
        n_samples: Total number of samples to generate
        flood_ratio: Proportion of positive (flood) samples (~15% matches real imbalance)
        seed: Random seed for reproducibility
        start_date: Start of the temporal range
        end_date: End of the temporal range

    Returns:
        DataFrame with all features and the flood_event target
    """
    rng = np.random.default_rng(seed)
    n_flood = int(n_samples * flood_ratio)
    n_normal = n_samples - n_flood

    # Generate timestamps spanning the date range
    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)
    total_hours = int((end - start).total_seconds() / 3600)

    records = []

    # ----- Normal conditions (no flood) -----
    for _ in range(n_normal):
        loc = rng.choice(LOCATION_PROFILES)
        hour_offset = rng.integers(0, total_hours)
        timestamp = start + pd.Timedelta(hours=int(hour_offset))

        record = _generate_normal_record(rng, loc, timestamp)
        record["flood_event"] = 0
        records.append(record)

    # ----- Flood conditions -----
    for _ in range(n_flood):
        loc = rng.choice(LOCATION_PROFILES)
        # Floods are more likely during monsoon (June-September)
        month = rng.choice([6, 7, 7, 8, 8, 8, 9, 9])
        year = rng.integers(2018, 2027)
        day = rng.integers(1, 29)
        hour = rng.integers(0, 24)
        try:
            timestamp = pd.Timestamp(year=int(year), month=int(month), day=int(day), hour=int(hour))
        except ValueError:
            timestamp = pd.Timestamp(year=int(year), month=int(month), day=15, hour=int(hour))

        record = _generate_flood_record(rng, loc, timestamp)
        record["flood_event"] = 1
        records.append(record)

    df = pd.DataFrame(records)

    # Shuffle
    df = df.sample(frac=1, random_state=seed).reset_index(drop=True)

    return df


def _generate_normal_record(rng, loc: dict, timestamp: pd.Timestamp) -> dict:
    """Generate a non-flood observation with realistic normal conditions."""
    month = timestamp.month
    is_monsoon = month in [6, 7, 8, 9]

    # Rainfall: low to moderate during non-monsoon, moderate during monsoon
    if is_monsoon:
        base_rain = rng.exponential(3.0)  # Mean 3mm/hr during monsoon
    else:
        base_rain = rng.exponential(0.5)  # Low outside monsoon

    rain_1h = round(max(0, base_rain + rng.normal(0, 1)), 1)
    rain_3h = round(rain_1h * rng.uniform(1.5, 3.0), 1)
    rain_6h = round(rain_3h * rng.uniform(1.2, 2.5), 1)
    rain_12h = round(rain_6h * rng.uniform(1.1, 2.0), 1)
    rain_24h = round(rain_12h * rng.uniform(1.1, 1.8), 1)
    rain_72h = round(rain_24h * rng.uniform(1.2, 2.5), 1)

    # Cap normal rainfall at moderate levels
    rain_24h = min(rain_24h, 80)
    rain_72h = min(rain_72h, 150)

    forecast_3h = round(rng.uniform(0, rain_3h * 1.2), 1)
    forecast_6h = round(rng.uniform(0, rain_6h * 1.1), 1)

    intensity = round(rain_1h / max(rain_6h / 6, 0.1), 2)
    acceleration = round(rng.normal(0, 2), 2)

    # Temperature varies with elevation and season
    base_temp = 30 - loc["elev"] * 0.006  # Lapse rate
    if is_monsoon:
        temp = round(base_temp + rng.normal(0, 3), 1)
    else:
        temp = round(base_temp - 5 + rng.normal(0, 4), 1)

    humidity = round(min(100, max(20, rng.normal(65 if is_monsoon else 45, 15))), 1)

    return {
        "timestamp": timestamp,
        "location_name": loc["name"],
        "rain_1h": rain_1h,
        "rain_3h": rain_3h,
        "rain_6h": rain_6h,
        "rain_12h": rain_12h,
        "rain_24h": rain_24h,
        "rain_72h": rain_72h,
        "forecast_rain_3h": forecast_3h,
        "forecast_rain_6h": forecast_6h,
        "rainfall_intensity": intensity,
        "rainfall_acceleration": acceleration,
        "temperature": temp,
        "humidity": humidity,
        "elevation": loc["elev"] + rng.normal(0, 20),
        "slope": max(0, loc["slope"] + rng.normal(0, 3)),
        "aspect": loc["aspect"] + rng.normal(0, 15),
        "terrain_ruggedness": max(0, loc["tri"] + rng.normal(0, 10)),
        "distance_to_waterbody": max(0, loc["dist_water"] + rng.normal(0, 0.1)),
        "historical_flood_frequency": loc["flood_freq"],
        "historical_event_severity": round(rng.uniform(0, 0.5), 2),
        "historical_flood_susceptibility": loc["flood_suscep"],
        "landslide_susceptibility": loc["landslide_suscep"],
        "blockage_indicator": round(rng.uniform(0, 0.2), 2),
        "distance_to_road": max(0, loc["dist_road"] + rng.normal(0, 0.05)),
        "road_exposure_indicator": round(rng.uniform(0, 0.3), 2),
        "bridge_exposure_indicator": round(rng.uniform(0, 0.2), 2),
    }


def _generate_flood_record(rng, loc: dict, timestamp: pd.Timestamp) -> dict:
    """Generate a flood observation with realistic extreme conditions."""
    # Floods require heavy rainfall
    rain_1h = round(rng.uniform(15, 60) + rng.exponential(10), 1)
    rain_3h = round(rain_1h * rng.uniform(2.0, 3.5), 1)
    rain_6h = round(rain_3h * rng.uniform(1.5, 2.5), 1)
    rain_12h = round(rain_6h * rng.uniform(1.3, 2.0), 1)
    rain_24h = round(rain_12h * rng.uniform(1.2, 1.8), 1)
    rain_72h = round(rain_24h * rng.uniform(1.3, 2.5), 1)

    # Ensure flood-level rainfall thresholds
    rain_24h = max(rain_24h, 80)
    rain_6h = max(rain_6h, 40)

    forecast_3h = round(rain_3h * rng.uniform(0.6, 1.4), 1)
    forecast_6h = round(rain_6h * rng.uniform(0.5, 1.3), 1)

    intensity = round(rain_1h / max(rain_6h / 6, 0.1), 2)
    acceleration = round(rng.uniform(2, 20), 2)  # Rainfall increasing during floods

    # Warm and humid during flood events
    base_temp = 30 - loc["elev"] * 0.006
    temp = round(base_temp + rng.normal(2, 2), 1)
    humidity = round(min(100, rng.uniform(80, 98)), 1)

    # Higher susceptibility locations flood more realistically
    suscep_boost = loc["flood_suscep"]

    return {
        "timestamp": timestamp,
        "location_name": loc["name"],
        "rain_1h": rain_1h,
        "rain_3h": rain_3h,
        "rain_6h": rain_6h,
        "rain_12h": rain_12h,
        "rain_24h": rain_24h,
        "rain_72h": rain_72h,
        "forecast_rain_3h": forecast_3h,
        "forecast_rain_6h": forecast_6h,
        "rainfall_intensity": intensity,
        "rainfall_acceleration": acceleration,
        "temperature": temp,
        "humidity": humidity,
        "elevation": loc["elev"] + rng.normal(0, 20),
        "slope": max(0, loc["slope"] + rng.normal(2, 3)),  # Slightly steeper on average
        "aspect": loc["aspect"] + rng.normal(0, 15),
        "terrain_ruggedness": max(0, loc["tri"] + rng.normal(5, 10)),
        "distance_to_waterbody": max(0, loc["dist_water"] * rng.uniform(0.3, 0.8)),  # Closer to water
        "historical_flood_frequency": loc["flood_freq"],
        "historical_event_severity": round(rng.uniform(0.4, 1.0), 2),
        "historical_flood_susceptibility": loc["flood_suscep"],
        "landslide_susceptibility": loc["landslide_suscep"],
        "blockage_indicator": round(rng.uniform(0.2, 0.9) * suscep_boost, 2),
        "distance_to_road": max(0, loc["dist_road"] + rng.normal(0, 0.05)),
        "road_exposure_indicator": round(rng.uniform(0.3, 1.0) * suscep_boost, 2),
        "bridge_exposure_indicator": round(rng.uniform(0.2, 0.9) * suscep_boost, 2),
    }


def save_dataset(df: pd.DataFrame, output_path: str) -> str:
    """Save dataset to CSV."""
    import os
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Dataset saved: {output_path}")
    print(f"  Samples: {len(df)}")
    print(f"  Flood events: {df['flood_event'].sum()} ({df['flood_event'].mean()*100:.1f}%)")
    print(f"  Features: {len(df.columns) - 3}")  # minus timestamp, location_name, target
    return output_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import os
    print("Generating synthetic training dataset...")
    df = generate_dataset(n_samples=5000, flood_ratio=0.15)
    output = os.path.join("data", "processed", "training_dataset.csv")
    save_dataset(df, output)
    print("\nSample flood record:")
    print(df[df["flood_event"] == 1].iloc[0].to_string())
