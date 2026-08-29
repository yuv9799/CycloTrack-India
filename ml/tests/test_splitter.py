"""
Tests for data.splitter.split_by_storm.

Run with:
    python -m pytest tests/test_splitter.py -v
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data.loader import load_cyclone_track
from data.splitter import split_by_storm

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_2000_2015 = PROJECT_ROOT / "sample_data" / "raw" / "cyclone_tracks_2000_2015.csv"


@pytest.fixture
def synthetic_storms():
    rows = []
    for i, storm_id in enumerate([f"S{i}" for i in range(10)]):
        start = pd.Timestamp("2000-01-01") + pd.Timedelta(days=30 * i)
        for h in range(4):
            rows.append(
                {
                    "storm_id": storm_id,
                    "timestamp": start + pd.Timedelta(hours=6 * h),
                    "latitude": 10.0 + h,
                    "longitude": -50.0 - h,
                    "wind_speed": 30.0 + h,
                }
            )
    return pd.DataFrame(rows)


def test_no_storm_appears_in_more_than_one_split(synthetic_storms):
    train, val, test = split_by_storm(synthetic_storms, train_frac=0.7, val_frac=0.15, test_frac=0.15)
    train_ids = set(train["storm_id"])
    val_ids = set(val["storm_id"])
    test_ids = set(test["storm_id"])
    assert not (train_ids & val_ids)
    assert not (train_ids & test_ids)
    assert not (val_ids & test_ids)
    assert train_ids | val_ids | test_ids == set(synthetic_storms["storm_id"])


def test_chronological_split_orders_by_first_observation(synthetic_storms):
    train, val, test = split_by_storm(synthetic_storms, chronological=True)
    assert train["timestamp"].max() <= val["timestamp"].min()
    assert val["timestamp"].max() <= test["timestamp"].min()


def test_fractions_must_sum_to_one(synthetic_storms):
    with pytest.raises(ValueError):
        split_by_storm(synthetic_storms, train_frac=0.5, val_frac=0.5, test_frac=0.5)


@pytest.mark.skipif(not RAW_2000_2015.exists(), reason="reference dataset not present")
def test_split_on_real_dataset_has_no_leakage():
    df = load_cyclone_track(str(RAW_2000_2015))
    train, val, test = split_by_storm(df)
    train_ids, val_ids, test_ids = set(train.storm_id), set(val.storm_id), set(test.storm_id)
    assert not (train_ids & val_ids)
    assert not (train_ids & test_ids)
    assert not (val_ids & test_ids)
    total_storms = df["storm_id"].nunique()
    assert len(train_ids) + len(val_ids) + len(test_ids) == total_storms
    # roughly 70/15/15 by storm count
    assert 0.65 <= len(train_ids) / total_storms <= 0.75
