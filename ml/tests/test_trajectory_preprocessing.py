"""
Tests for preprocessing.trajectory_preprocessing.

Includes:
- Unit tests on small synthetic fixtures (fast, deterministic).
- A regression test against the real uploaded reference dataset
  (sample_data/processed/cyclone_tracks_features_2000_2015.csv),
  which was independently pre-computed and is used here as a
  golden-file check that our formulas match it exactly.

Run with:
    python -m pytest tests/test_trajectory_preprocessing.py -v
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data.loader import load_cyclone_track
from preprocessing.trajectory_preprocessing import (
    haversine_distance_km,
    movement_direction_deg,
    engineer_trajectory_features,
    wind_speed_to_category,
    create_trajectory_sequences,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_2000_2015 = PROJECT_ROOT / "sample_data" / "raw" / "cyclone_tracks_2000_2015.csv"
FEATURES_REFERENCE = PROJECT_ROOT / "sample_data" / "processed" / "cyclone_tracks_features_2000_2015.csv"


# ------------------------------------------------------------
# Synthetic fixtures
# ------------------------------------------------------------

@pytest.fixture
def two_storm_df():
    """Two short synthetic storms to exercise per-storm grouping / no-leakage behaviour."""
    return pd.DataFrame(
        {
            "storm_id": ["S1", "S1", "S1", "S2", "S2"],
            "timestamp": pd.to_datetime(
                [
                    "2020-01-01 00:00", "2020-01-01 06:00", "2020-01-01 12:00",
                    "2020-06-01 00:00", "2020-06-01 06:00",
                ]
            ),
            "latitude": [10.0, 10.5, 11.0, 20.0, 19.5],
            "longitude": [-50.0, -50.5, -51.0, 80.0, 80.5],
            "wind_speed": [30.0, 35.0, 40.0, 60.0, 65.0],
            "pressure": [1005.0, 1002.0, 999.0, 990.0, 985.0],
        }
    )


# ------------------------------------------------------------
# Haversine / bearing
# ------------------------------------------------------------

def test_haversine_zero_distance_for_same_point():
    assert haversine_distance_km(10.0, -50.0, 10.0, -50.0) == pytest.approx(0.0)


def test_haversine_known_distance():
    # ~1 degree of latitude ~ 111 km
    d = haversine_distance_km(0.0, 0.0, 1.0, 0.0)
    assert d == pytest.approx(111.19, abs=0.5)


def test_movement_direction_is_planar_atan2():
    # due north: lat increases, lon constant -> 0 degrees
    assert movement_direction_deg(10.0, -50.0, 11.0, -50.0) == pytest.approx(0.0)
    # due east: lon increases, lat constant -> 90 degrees
    assert movement_direction_deg(10.0, -50.0, 10.0, -49.0) == pytest.approx(90.0)


# ------------------------------------------------------------
# engineer_trajectory_features
# ------------------------------------------------------------

def test_first_observation_of_each_storm_has_nan_movement(two_storm_df):
    out = engineer_trajectory_features(two_storm_df)
    first_rows = out.groupby("storm_id").head(1)
    assert first_rows["movement_distance_km"].isna().all()
    assert first_rows["prev_lat"].isna().all()


def test_no_cross_storm_leakage_in_prev_columns(two_storm_df):
    out = engineer_trajectory_features(two_storm_df)
    s2_first = out[out["storm_id"] == "S2"].iloc[0]
    # S2's first row must NOT pick up S1's last observation as "previous"
    assert pd.isna(s2_first["prev_lat"])
    assert pd.isna(s2_first["wind_change"])


def test_rolling_avg_wind_resets_per_storm(two_storm_df):
    out = engineer_trajectory_features(two_storm_df, rolling_window=3)
    s2 = out[out["storm_id"] == "S2"].reset_index(drop=True)
    # S2 has only 2 rows; rolling(window=3, min_periods=1) over just S2's own wind values
    assert s2.loc[0, "rolling_avg_wind_3"] == pytest.approx(60.0)
    assert s2.loc[1, "rolling_avg_wind_3"] == pytest.approx((60.0 + 65.0) / 2)


def test_wind_and_pressure_change_signs(two_storm_df):
    out = engineer_trajectory_features(two_storm_df)
    s1 = out[out["storm_id"] == "S1"].reset_index(drop=True)
    assert s1.loc[1, "wind_change"] == pytest.approx(5.0)       # 35 - 30
    assert s1.loc[1, "pressure_change"] == pytest.approx(-3.0)  # 1002 - 1005


# ------------------------------------------------------------
# wind_speed_to_category
# ------------------------------------------------------------

def test_wind_speed_to_category_boundaries():
    assert wind_speed_to_category(20) == "Tropical Depression"
    assert wind_speed_to_category(50) == "Tropical Storm"
    assert wind_speed_to_category(150) == "Category 5 (Major)"


def test_wind_speed_to_category_handles_nan():
    assert wind_speed_to_category(float("nan")) == "Unknown"


# ------------------------------------------------------------
# create_trajectory_sequences
# ------------------------------------------------------------

def test_create_trajectory_sequences_shapes(two_storm_df):
    engineered = engineer_trajectory_features(two_storm_df)
    # too short for input_steps=5 -> should produce zero sequences gracefully, not raise
    X, y, meta = create_trajectory_sequences(engineered, input_steps=2, forecast_hours=(6,), step_hours=6.0)
    assert X.shape[0] == y.shape[0] == len(meta)
    if X.shape[0] > 0:
        assert X.shape[1] == 2  # input_steps
        assert y.shape[1] == 1  # one horizon


def test_create_trajectory_sequences_rejects_unreachable_horizon(two_storm_df):
    engineered = engineer_trajectory_features(two_storm_df)
    with pytest.raises(ValueError):
        create_trajectory_sequences(engineered, input_steps=2, forecast_hours=(5,), step_hours=6.0)


# ------------------------------------------------------------
# Regression test against the real uploaded reference dataset
# ------------------------------------------------------------

@pytest.mark.skipif(not RAW_2000_2015.exists() or not FEATURES_REFERENCE.exists(), reason="reference dataset not present")
def test_engineered_features_match_real_reference_dataset():
    raw = load_cyclone_track(str(RAW_2000_2015))
    engineered = engineer_trajectory_features(raw)
    reference = load_cyclone_track(str(FEATURES_REFERENCE))

    merged = engineered.merge(
        reference[
            [
                "storm_id", "timestamp", "movement_distance_km", "movement_direction_deg",
                "velocity_kmh", "wind_change", "pressure_change", "rolling_avg_wind_3",
            ]
        ],
        on=["storm_id", "timestamp"],
        suffixes=("_mine", "_ref"),
    )
    assert len(merged) == len(reference)

    for col in [
        "movement_distance_km", "movement_direction_deg", "velocity_kmh",
        "wind_change", "pressure_change", "rolling_avg_wind_3",
    ]:
        a, b = merged[f"{col}_mine"], merged[f"{col}_ref"]
        both_nan = a.isna() & b.isna()
        assert np.allclose(a[~both_nan], b[~both_nan], atol=1e-6), f"mismatch in {col}"


@pytest.mark.skipif(not FEATURES_REFERENCE.exists(), reason="reference dataset not present")
def test_wind_speed_to_category_matches_real_reference_dataset():
    reference = load_cyclone_track(str(FEATURES_REFERENCE))
    predicted = reference["wind_speed"].apply(wind_speed_to_category)
    assert (predicted == reference["intensity_category"]).all()
