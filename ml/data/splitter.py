"""
Train/validation/test splitting for cyclone track data.

Cyclone track and trajectory data is time-series-per-storm — randomly
shuffling rows (or even randomly shuffling storms without regard to
time) risks leaking information: consecutive observations of the same
storm are highly correlated, so if storm X's early hours end up in
train and its later hours end up in test, the model effectively sees
the answer during training.

Rule (per spec): split by storm_id, chronologically, so the same storm
never appears in more than one split. Default ratios: 70/15/15.
"""

from __future__ import annotations

from typing import Optional, Tuple

import numpy as np
import pandas as pd

from utils.logger import get_logger

logger = get_logger(__name__)


def split_by_storm(
    df: pd.DataFrame,
    storm_col: str = "storm_id",
    time_col: str = "timestamp",
    train_frac: float = 0.70,
    val_frac: float = 0.15,
    test_frac: float = 0.15,
    random_seed: Optional[int] = 42,
    chronological: bool = True,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Split a cyclone track DataFrame into train/val/test by storm_id, so
    no storm's observations appear in more than one split.

    Parameters
    ----------
    df : pd.DataFrame
        Track data with a storm identifier column and (if
        `chronological=True`) a timestamp column.
    train_frac, val_frac, test_frac : float
        Must sum to ~1.0. Fraction of *storms* (not rows) assigned to
        each split.
    random_seed : int | None
        Seed for the split. Ignored when `chronological=True` (the
        split is then fully deterministic by storm start date).
    chronological : bool
        If True (default, and the safer choice for a forecasting
        model that will run on future storms): storms are ordered by
        their first observation's timestamp, and the earliest
        `train_frac` of storms go to train, the next `val_frac` to
        val, and the most recent `test_frac` to test. This mirrors how
        the model will actually be used (trained on the past, tested
        on more recent storms) and prevents look-ahead leakage.
        If False: storms are shuffled randomly (still storm-level, so
        no leakage within a storm) — use only for quick experiments,
        not for the final reported metrics.

    Returns
    -------
    (train_df, val_df, test_df) : tuple of pd.DataFrame
    """
    total = train_frac + val_frac + test_frac
    if not np.isclose(total, 1.0, atol=1e-6):
        raise ValueError(f"train_frac + val_frac + test_frac must sum to 1.0, got {total}")

    if storm_col not in df.columns:
        raise ValueError(f"split_by_storm: '{storm_col}' not found in DataFrame columns.")

    if chronological:
        if time_col not in df.columns:
            raise ValueError(
                f"split_by_storm: chronological=True requires '{time_col}' column."
            )
        storm_start = df.groupby(storm_col)[time_col].min().sort_values()
        storm_ids = storm_start.index.to_numpy()
    else:
        storm_ids = df[storm_col].unique()
        rng = np.random.default_rng(random_seed)
        rng.shuffle(storm_ids)

    n = len(storm_ids)
    n_train = int(round(n * train_frac))
    n_val = int(round(n * val_frac))
    # give any rounding remainder to test so all storms are always covered
    n_test = n - n_train - n_val

    train_ids = set(storm_ids[:n_train])
    val_ids = set(storm_ids[n_train : n_train + n_val])
    test_ids = set(storm_ids[n_train + n_val :])

    train_df = df[df[storm_col].isin(train_ids)].reset_index(drop=True)
    val_df = df[df[storm_col].isin(val_ids)].reset_index(drop=True)
    test_df = df[df[storm_col].isin(test_ids)].reset_index(drop=True)

    # sanity check: no storm should appear in more than one split
    overlap = (train_ids & val_ids) | (train_ids & test_ids) | (val_ids & test_ids)
    if overlap:
        raise AssertionError(f"Storm leakage detected across splits: {overlap}")

    logger.info(
        f"split_by_storm: {n} storms -> train={len(train_ids)} ({len(train_df)} rows), "
        f"val={len(val_ids)} ({len(val_df)} rows), test={len(test_ids)} ({len(test_df)} rows), "
        f"chronological={chronological}"
    )

    if chronological:
        logger.info(
            f"  train storms: {storm_start.index[0]!s} .. {storm_start.index[n_train-1]!s} "
            f"(by first-obs date {storm_start.iloc[0]} .. {storm_start.iloc[n_train-1]})"
        )

    return train_df, val_df, test_df
