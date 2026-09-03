"""
NeerNetra — Temporal Data Splitter
=====================================
Splits data using temporal ordering, NOT random row-wise splitting.

From Section 6.6:
  "Avoid random row-wise splitting if observations from the same event
   appear in both training and testing."

Strategy:
  Older events → Training (70%)
  More recent events → Validation (15%)
  Latest events → Testing (15%)

This better approximates real-world deployment where the model
must predict future events it has never seen.
"""

import pandas as pd
import numpy as np
from typing import Tuple


def temporal_split(
    df: pd.DataFrame,
    timestamp_col: str = "timestamp",
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Split dataset by temporal ordering.

    Args:
        df: DataFrame with a timestamp column
        timestamp_col: Name of the timestamp column
        train_ratio: Fraction for training
        val_ratio: Fraction for validation
        test_ratio: Fraction for testing

    Returns:
        (train_df, val_df, test_df)
    """
    assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-6, \
        "Ratios must sum to 1.0"

    # Sort by timestamp
    df_sorted = df.sort_values(timestamp_col).reset_index(drop=True)

    n = len(df_sorted)
    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))

    train_df = df_sorted.iloc[:train_end].copy()
    val_df = df_sorted.iloc[train_end:val_end].copy()
    test_df = df_sorted.iloc[val_end:].copy()

    # Report split statistics
    print("Temporal Split:")
    print(f"  Training:   {len(train_df):,} samples "
          f"({train_df[timestamp_col].min()} -- {train_df[timestamp_col].max()})")
    print(f"  Validation: {len(val_df):,} samples "
          f"({val_df[timestamp_col].min()} -- {val_df[timestamp_col].max()})")
    print(f"  Test:       {len(test_df):,} samples "
          f"({test_df[timestamp_col].min()} -- {test_df[timestamp_col].max()})")

    # Report class balance per split
    for name, split_df in [("Train", train_df), ("Val", val_df), ("Test", test_df)]:
        if "flood_event" in split_df.columns:
            flood_pct = split_df["flood_event"].mean() * 100
            print(f"  {name} flood ratio: {flood_pct:.1f}%")

    return train_df, val_df, test_df
