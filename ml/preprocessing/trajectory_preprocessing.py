"""
Trajectory preprocessing / feature engineering for CycloneAI.

Turns a raw, chronologically-sorted cyclone track DataFrame (storm_id,
timestamp, latitude, longitude, wind_speed, pressure, ...) into the
engineered feature set used by the intensity and trajectory models:

    prev_lat, prev_lon, prev_wind_speed, prev_pressure,
    time_diff_hours, movement_distance_km, movement_direction_deg,
    velocity_kmh, wind_change, pressure_change, rolling_avg_wind_3

All formulas below were verified row-for-row against a real,
pre-engineered reference file (568 storms / ~16k rows) so this is not
a from-scratch guess at the spec:

- Distance: standard Haversine, Earth radius = 6371 km.
- Direction: a *planar* bearing — degrees(atan2(delta_lon, delta_lat))
  normalized to [0, 360). This is simpler than a true great-circle
  bearing and matches the reference data exactly; it's adequate at the
  short inter-observation distances typical of 6-hourly track data.
- Velocity: distance_km / time_diff_hours.
- wind_change / pressure_change: simple deltas from the previous
  observation of the *same storm*.
- rolling_avg_wind_3: rolling mean of wind_speed, window=3,
  min_periods=1, computed per storm (never across storm boundaries).

Everything here operates per storm_id group — a "previous observation"
is only ever the previous row of the *same* storm, never a different
one stacked above it in the DataFrame.
"""

from __future__ import annotations

from typing import List, Optional, Sequence

import numpy as np
import pandas as pd

from utils.logger import get_logger

logger = get_logger(__name__)

EARTH_RADIUS_KM = 6371.0


def haversine_distance_km(
    lat1: np.ndarray, lon1: np.ndarray, lat2: np.ndarray, lon2: np.ndarray
) -> np.ndarray:
    """
    Great-circle distance in km between paired (lat1, lon1) and
    (lat2, lon2) points (vectorized, works on scalars or arrays).
    """
    lat1r, lon1r, lat2r, lon2r = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2r - lat1r
    dlon = lon2r - lon1r
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1r) * np.cos(lat2r) * np.sin(dlon / 2.0) ** 2
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))


def movement_direction_deg(
    lat1: np.ndarray, lon1: np.ndarray, lat2: np.ndarray, lon2: np.ndarray
) -> np.ndarray:
    """
    Planar movement direction in degrees [0, 360), matching the
    reference dataset's convention: 0=north, 90=east, 180=south,
    270=west relative to (lat, lon) treated as a flat plane.
    """
    dlat = np.asarray(lat2) - np.asarray(lat1)
    dlon = np.asarray(lon2) - np.asarray(lon1)
    ang = np.degrees(np.arctan2(dlon, dlat))
    return (ang + 360.0) % 360.0


def engineer_trajectory_features(
    df: pd.DataFrame,
    storm_col: str = "storm_id",
    time_col: str = "timestamp",
    lat_col: str = "latitude",
    lon_col: str = "longitude",
    wind_col: str = "wind_speed",
    pressure_col: str = "pressure",
    rolling_window: int = 3,
) -> pd.DataFrame:
    """
    Add trajectory/kinematic features to a standardized cyclone-track
    DataFrame. Must be called on data that already has canonical
    column names (see `data.loader.standardize_columns`).

    Parameters
    ----------
    df : pd.DataFrame
        Track data with at least storm_id, timestamp, latitude,
        longitude columns; wind_speed/pressure are used when present.
    storm_col, time_col, lat_col, lon_col, wind_col, pressure_col : str
        Column name overrides, in case the caller wants to run this on
        non-canonical column names directly.
    rolling_window : int
        Window size for the rolling wind-speed average (default 3,
        matching the reference dataset's `rolling_avg_wind_3`).

    Returns
    -------
    pd.DataFrame
        A copy of `df`, sorted by (storm_id, timestamp), with the
        following columns added: prev_lat, prev_lon, prev_wind_speed,
        prev_pressure, time_diff_hours, movement_distance_km,
        movement_direction_deg, velocity_kmh, wind_change,
        pressure_change, rolling_avg_wind_{window}.
    """
    required = [storm_col, time_col, lat_col, lon_col]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"engineer_trajectory_features: missing required column(s) {missing}")

    out = df.copy()
    if not np.issubdtype(out[time_col].dtype, np.datetime64):
        out[time_col] = pd.to_datetime(out[time_col], errors="coerce")

    out = out.sort_values([storm_col, time_col]).reset_index(drop=True)
    grp = out.groupby(storm_col, sort=False)

    out["prev_lat"] = grp[lat_col].shift(1)
    out["prev_lon"] = grp[lon_col].shift(1)

    out["time_diff_hours"] = (
        out[time_col] - grp[time_col].shift(1)
    ).dt.total_seconds() / 3600.0

    out["movement_distance_km"] = haversine_distance_km(
        out["prev_lat"].to_numpy(dtype=float),
        out["prev_lon"].to_numpy(dtype=float),
        out[lat_col].to_numpy(dtype=float),
        out[lon_col].to_numpy(dtype=float),
    )
    out["movement_direction_deg"] = movement_direction_deg(
        out["prev_lat"].to_numpy(dtype=float),
        out["prev_lon"].to_numpy(dtype=float),
        out[lat_col].to_numpy(dtype=float),
        out[lon_col].to_numpy(dtype=float),
    )
    # velocity / distance / direction are only meaningful where there was
    # a previous observation of the *same* storm — NaN propagates naturally
    # from prev_lat/prev_lon being NaN, but guard divide-by-zero explicitly.
    with np.errstate(divide="ignore", invalid="ignore"):
        out["velocity_kmh"] = np.where(
            out["time_diff_hours"] > 0,
            out["movement_distance_km"] / out["time_diff_hours"],
            np.nan,
        )
    first_obs_mask = out["prev_lat"].isna()
    out.loc[first_obs_mask, ["movement_distance_km", "movement_direction_deg", "velocity_kmh"]] = np.nan

    if wind_col in out.columns:
        out["prev_wind_speed"] = grp[wind_col].shift(1)
        out["wind_change"] = out[wind_col] - out["prev_wind_speed"]
        out[f"rolling_avg_wind_{rolling_window}"] = grp[wind_col].transform(
            lambda s: s.rolling(window=rolling_window, min_periods=1).mean()
        )
    else:
        logger.warning(f"Column '{wind_col}' not found — skipping wind-derived features.")

    if pressure_col in out.columns:
        out["prev_pressure"] = grp[pressure_col].shift(1)
        out["pressure_change"] = out[pressure_col] - out["prev_pressure"]
    else:
        logger.warning(f"Column '{pressure_col}' not found — skipping pressure-derived features.")

    logger.info(
        f"Engineered trajectory features for {out[storm_col].nunique()} storms, {len(out)} rows."
    )
    return out


def wind_speed_to_category(wind_kt: float, thresholds: Optional[List[dict]] = None) -> str:
    """
    Map a wind speed (knots) to an intensity category name using a
    configurable, ascending list of {"name", "max_wind_kt"} thresholds
    (see config/classes.yaml -> dataset_intensity_categories). The
    first threshold whose max_wind_kt >= wind_kt wins.
    """
    if thresholds is None:
        from utils.config import get_classes  # local import to avoid cycles at module load

        thresholds = get_classes()["dataset_intensity_categories"]

    if wind_kt is None or (isinstance(wind_kt, float) and np.isnan(wind_kt)):
        return "Unknown"

    for band in thresholds:
        if wind_kt <= band["max_wind_kt"]:
            return band["name"]
    return thresholds[-1]["name"]


def create_trajectory_sequences(
    df: pd.DataFrame,
    input_steps: int = 5,
    forecast_hours: Sequence[int] = (6, 12, 24, 48),
    storm_col: str = "storm_id",
    time_col: str = "timestamp",
    feature_cols: Optional[List[str]] = None,
    target_cols: Sequence[str] = ("latitude", "longitude"),
    step_hours: float = 6.0,
) -> "tuple[np.ndarray, np.ndarray, list]":
    """
    Build (X, y) sequences for the LSTM/GRU trajectory model.

    For every storm, slides a window of `input_steps` consecutive
    6-hourly observations and pairs it with the target lat/lon at each
    requested forecast horizon (e.g. +6h, +12h, +24h, +48h ahead of the
    *last* input step). Sequences that would require data past the end
    of a storm's track, or that cross into a different storm, are
    skipped — this is what keeps storms from leaking into each other.

    Parameters
    ----------
    df : pd.DataFrame
        Output of `engineer_trajectory_features` (or any DataFrame with
        the required feature/target columns), one row per 6-hourly
        observation, already sorted by (storm_id, timestamp).
    input_steps : int
        Number of past observations to feed the model (default 5).
    forecast_hours : sequence of int
        Forecast horizons in hours (default 6/12/24/48h, per spec).
        Must be reachable at the dataset's `step_hours` cadence.
    feature_cols : list[str] | None
        Columns to use as model input features. Defaults to
        [latitude, longitude, wind_speed, pressure, velocity_kmh,
        movement_direction_deg, pressure_change, wind_change].
    target_cols : sequence of str
        Columns to predict at each forecast horizon (default lat/lon).
    step_hours : float
        Expected spacing between consecutive observations (default 6h,
        the standard best-track cadence). Used to convert forecast
        hours into row offsets.

    Returns
    -------
    X : np.ndarray, shape (n_sequences, input_steps, n_features)
    y : np.ndarray, shape (n_sequences, n_horizons, n_targets)
    meta : list of dict
        One entry per sequence: {"storm_id", "anchor_timestamp"} for
        traceability back to the source data.
    """
    if feature_cols is None:
        feature_cols = [
            c
            for c in [
                "latitude",
                "longitude",
                "wind_speed",
                "pressure",
                "velocity_kmh",
                "movement_direction_deg",
                "pressure_change",
                "wind_change",
            ]
            if c in df.columns
        ]

    missing_targets = [c for c in target_cols if c not in df.columns]
    if missing_targets:
        raise ValueError(f"create_trajectory_sequences: missing target column(s) {missing_targets}")

    horizon_offsets = []
    for h in forecast_hours:
        if h % step_hours != 0:
            raise ValueError(
                f"forecast_hour={h} is not reachable at step_hours={step_hours} cadence."
            )
        horizon_offsets.append(int(h / step_hours))
    max_offset = max(horizon_offsets)

    X_list: List[np.ndarray] = []
    y_list: List[np.ndarray] = []
    meta: List[dict] = []

    for storm_id, storm_df in df.groupby(storm_col, sort=False):
        storm_df = storm_df.sort_values(time_col).reset_index(drop=True)
        n = len(storm_df)
        feat_arr = storm_df[feature_cols].to_numpy(dtype=float)
        targ_arr = storm_df[list(target_cols)].to_numpy(dtype=float)

        last_anchor = n - 1 - max_offset
        for anchor in range(input_steps - 1, last_anchor + 1):
            window = feat_arr[anchor - input_steps + 1 : anchor + 1]
            if np.isnan(window).any():
                continue  # skip windows touching missing/first-obs NaNs
            targets = np.stack([targ_arr[anchor + off] for off in horizon_offsets])
            if np.isnan(targets).any():
                continue
            X_list.append(window)
            y_list.append(targets)
            meta.append(
                {
                    "storm_id": storm_id,
                    "anchor_timestamp": storm_df.loc[anchor, time_col],
                }
            )

    if not X_list:
        logger.warning("create_trajectory_sequences: produced 0 sequences — check input_steps/forecast_hours vs data length.")
        return np.empty((0, input_steps, len(feature_cols))), np.empty((0, len(horizon_offsets), len(target_cols))), []

    X = np.stack(X_list)
    y = np.stack(y_list)
    logger.info(
        f"Built {len(X)} trajectory sequences from {df[storm_col].nunique()} storms "
        f"(input_steps={input_steps}, horizons={list(forecast_hours)}h)."
    )
    return X, y, meta
