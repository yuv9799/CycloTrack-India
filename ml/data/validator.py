"""
Dataset validation utilities for CycloneAI.

These checks run *after* `loader.py` has standardized column names.
They never raise on soft issues (e.g. missing values) — those are
logged as warnings and reported back to the caller so upstream code
(EDA notebooks, training scripts, or the backend) can decide how to
react. Hard failures (missing required columns) raise `ValidationError`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from utils.config import get_config
from utils.logger import get_logger

logger = get_logger(__name__)


class ValidationError(Exception):
    """Raised when a dataset fails a hard/required validation check."""


@dataclass
class ValidationReport:
    """Structured, JSON-serializable result of a validation run."""

    is_valid: bool
    n_rows: int
    n_columns: int
    missing_required_columns: List[str] = field(default_factory=list)
    missing_value_counts: Dict[str, int] = field(default_factory=dict)
    missing_value_pct: Dict[str, float] = field(default_factory=dict)
    duplicate_rows: int = 0
    out_of_range_columns: Dict[str, int] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "n_rows": self.n_rows,
            "n_columns": self.n_columns,
            "missing_required_columns": self.missing_required_columns,
            "missing_value_counts": self.missing_value_counts,
            "missing_value_pct": self.missing_value_pct,
            "duplicate_rows": self.duplicate_rows,
            "out_of_range_columns": self.out_of_range_columns,
            "warnings": self.warnings,
        }


# Sane physical bounds used only to flag likely data-entry errors,
# never to silently drop rows.
_PHYSICAL_RANGES = {
    "latitude": (-90.0, 90.0),
    "longitude": (-180.0, 180.0),
    "wind_speed": (0.0, 350.0),        # knots — generous upper bound
    "pressure": (850.0, 1050.0),       # hPa
    "humidity": (0.0, 100.0),          # percent
}


def validate_track_dataframe(
    df: pd.DataFrame,
    required_columns: Optional[List[str]] = None,
    raise_on_missing_required: bool = True,
) -> ValidationReport:
    """
    Validate a (already column-standardized) cyclone track / weather
    DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Standardized DataFrame (see `loader.standardize_columns`).
    required_columns : list[str] | None
        Columns that must be present. Defaults to
        config.yaml -> data.required_columns_track.
    raise_on_missing_required : bool
        If True, raise ValidationError when required columns are absent.
        If False, just record them in the report (useful for exploratory
        checks where you want a report even on bad data).

    Returns
    -------
    ValidationReport
    """
    if required_columns is None:
        required_columns = get_config()["data"]["required_columns_track"]

    n_rows, n_cols = df.shape
    warnings: List[str] = []

    missing_required = [c for c in required_columns if c not in df.columns]
    if missing_required:
        msg = f"Missing required column(s): {missing_required}"
        logger.warning(msg)
        warnings.append(msg)
        if raise_on_missing_required:
            raise ValidationError(msg)

    # Missing values
    missing_counts = df.isna().sum()
    missing_counts = missing_counts[missing_counts > 0]
    missing_value_counts = missing_counts.to_dict()
    missing_value_pct = (
        (missing_counts / max(n_rows, 1) * 100).round(2).to_dict() if n_rows else {}
    )
    for col, pct in missing_value_pct.items():
        if pct > 30:
            warnings.append(f"Column '{col}' has {pct}% missing values — consider dropping or imputing carefully.")

    # Duplicate rows
    duplicate_rows = int(df.duplicated().sum())
    if duplicate_rows > 0:
        warnings.append(f"{duplicate_rows} duplicate row(s) detected.")

    # Out-of-physical-range checks
    out_of_range: Dict[str, int] = {}
    for col, (lo, hi) in _PHYSICAL_RANGES.items():
        if col in df.columns:
            numeric = pd.to_numeric(df[col], errors="coerce")
            bad = int(((numeric < lo) | (numeric > hi)).sum())
            if bad > 0:
                out_of_range[col] = bad
                warnings.append(f"Column '{col}' has {bad} value(s) outside expected range [{lo}, {hi}].")

    for w in warnings:
        logger.warning(w)

    is_valid = len(missing_required) == 0

    report = ValidationReport(
        is_valid=is_valid,
        n_rows=n_rows,
        n_columns=n_cols,
        missing_required_columns=missing_required,
        missing_value_counts={k: int(v) for k, v in missing_value_counts.items()},
        missing_value_pct={k: float(v) for k, v in missing_value_pct.items()},
        duplicate_rows=duplicate_rows,
        out_of_range_columns=out_of_range,
        warnings=warnings,
    )

    logger.info(
        f"Validation complete: {n_rows} rows, {n_cols} cols, "
        f"valid={is_valid}, warnings={len(warnings)}"
    )
    return report


def handle_missing_values(
    df: pd.DataFrame,
    strategy: str = "interpolate",
    columns: Optional[List[str]] = None,
    group_col: Optional[str] = "storm_id",
) -> pd.DataFrame:
    """
    Fill missing values in numeric columns using a configurable strategy.

    Parameters
    ----------
    df : pd.DataFrame
    strategy : str
        One of "interpolate" (time-aware linear interpolation, good for
        time-series), "ffill", "bfill", "mean", "median", or "drop".
    columns : list[str] | None
        Restrict handling to these columns. Defaults to all numeric columns.
    group_col : str | None
        For "interpolate"/"ffill"/"bfill", fill within each group
        independently (e.g. per storm_id) so values never leak across
        unrelated time-series that happen to be stacked in the same
        DataFrame. On real multi-storm track data, interpolating
        globally will happily backfill storm A's pressure from storm Z
        decades later — this is the whole reason this parameter exists.
        Set to None to fill globally (matches old behaviour). Ignored
        for "mean"/"median"/"drop".

    Returns
    -------
    pd.DataFrame
        A copy of `df` with missing values handled.
    """
    df = df.copy()
    numeric_cols = columns or df.select_dtypes(include=[np.number]).columns.tolist()

    if strategy == "drop":
        before = len(df)
        df = df.dropna(subset=numeric_cols)
        logger.info(f"Dropped {before - len(df)} row(s) with missing values in {numeric_cols}.")
        return df

    use_grouping = group_col is not None and group_col in df.columns and strategy in ("interpolate", "ffill", "bfill")

    for col in numeric_cols:
        if col not in df.columns:
            continue
        n_missing = int(df[col].isna().sum())
        if n_missing == 0:
            continue

        if strategy == "interpolate":
            if use_grouping:
                df[col] = df.groupby(group_col, sort=False)[col].transform(
                    lambda s: s.interpolate(method="linear", limit_direction="both")
                )
            else:
                df[col] = df[col].interpolate(method="linear", limit_direction="both")
        elif strategy == "ffill":
            if use_grouping:
                df[col] = df.groupby(group_col, sort=False)[col].transform(lambda s: s.ffill().bfill())
            else:
                df[col] = df[col].ffill().bfill()
        elif strategy == "bfill":
            if use_grouping:
                df[col] = df.groupby(group_col, sort=False)[col].transform(lambda s: s.bfill().ffill())
            else:
                df[col] = df[col].bfill().ffill()
        elif strategy == "mean":
            df[col] = df[col].fillna(df[col].mean())
        elif strategy == "median":
            df[col] = df[col].fillna(df[col].median())
        else:
            raise ValueError(f"Unknown missing-value strategy: {strategy}")

        remaining = int(df[col].isna().sum())
        logger.info(
            f"Filled {n_missing - remaining} missing value(s) in '{col}' using strategy='{strategy}'"
            + (f" (grouped by {group_col})" if use_grouping else "")
            + (f"; {remaining} still missing (e.g. an entire storm has no data)." if remaining else ".")
        )

    return df
