"""
Phase 1 tests: dataset loading, column standardization, and validation.

Run with:
    python -m pytest tests/test_data_loading.py -v
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data.loader import load_cyclone_track, standardize_columns
from data.validator import (
    ValidationError,
    validate_track_dataframe,
    handle_missing_values,
)

SAMPLE_TRACK = Path(__file__).resolve().parents[1] / "sample_data" / "sample" / "tracks" / "sample_storm_A.csv"


def test_sample_file_exists():
    assert SAMPLE_TRACK.exists(), "Sample track CSV should exist for Phase 1 tests."


def test_load_cyclone_track_standardizes_columns():
    df = load_cyclone_track(SAMPLE_TRACK)
    expected = {"storm_id", "storm_name", "timestamp", "latitude", "longitude",
                "wind_speed", "pressure", "sea_surface_temperature", "humidity"}
    assert expected.issubset(set(df.columns))


def test_load_cyclone_track_sorts_by_timestamp():
    df = load_cyclone_track(SAMPLE_TRACK)
    assert df["timestamp"].is_monotonic_increasing


def test_standardize_columns_is_alias_agnostic():
    raw = pd.DataFrame({"Lat": [1.0], "LON": [2.0], "windspeed": [50.0]})
    df = standardize_columns(raw)
    assert "latitude" in df.columns
    assert "longitude" in df.columns
    assert "wind_speed" in df.columns


def test_validate_track_dataframe_detects_missing_required_column():
    df = pd.DataFrame({"latitude": [1.0], "longitude": [2.0]})  # no timestamp
    with pytest.raises(ValidationError):
        validate_track_dataframe(df, raise_on_missing_required=True)


def test_validate_track_dataframe_reports_missing_values():
    df = load_cyclone_track(SAMPLE_TRACK)
    report = validate_track_dataframe(df, raise_on_missing_required=False)
    assert report.is_valid is True
    assert "wind_speed" in report.missing_value_counts


def test_handle_missing_values_interpolate_fills_gaps():
    df = load_cyclone_track(SAMPLE_TRACK)
    assert df["wind_speed"].isna().sum() > 0
    clean = handle_missing_values(df, strategy="interpolate")
    assert clean["wind_speed"].isna().sum() == 0


def test_handle_missing_values_drop_strategy():
    df = load_cyclone_track(SAMPLE_TRACK)
    before = len(df)
    clean = handle_missing_values(df, strategy="drop", columns=["wind_speed"])
    assert len(clean) == before - df["wind_speed"].isna().sum()


def test_handle_missing_values_does_not_leak_across_storms():
    """
    Regression test: interpolating a column with group_col='storm_id'
    must never fill a storm's missing leading/trailing values using a
    different storm's data. Uses the real multi-storm historical file.
    """
    full_path = Path(__file__).resolve().parents[1] / "sample_data" / "raw" / "cyclone_tracks_full_1851_2015.csv"
    if not full_path.exists():
        pytest.skip("full historical reference dataset not present")

    df = load_cyclone_track(full_path)
    # AL011851 has pressure entirely missing for its early observations
    storm = df[df["storm_id"] == "AL011851"]
    assert storm["pressure"].isna().any()

    clean = handle_missing_values(df, strategy="interpolate", columns=["pressure"], group_col="storm_id")
    clean_storm = clean[clean["storm_id"] == "AL011851"]

    # If a whole storm's pressure is missing, per-storm interpolation
    # cannot invent a value from nothing -- it should stay NaN rather
    # than silently pulling in an unrelated storm's pressure.
    if storm["pressure"].isna().all():
        assert clean_storm["pressure"].isna().all()
    else:
        assert clean_storm["pressure"].isna().sum() == 0
