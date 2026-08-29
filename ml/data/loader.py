"""
Flexible dataset loader for CycloneAI.

Handles tabular cyclone-track / weather data (CSV, JSON) with a
configurable column-alias mapping so the pipeline is not tied to any
single dataset's naming convention (e.g. IBTrACS, IMD best-track, or a
custom hackathon dataset).

Design goals (per spec):
- Validate files before loading.
- Standardize column names to canonical form.
- Handle missing values sensibly.
- Log warnings instead of failing hard on non-critical issues.
- Return clean pandas DataFrames.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Union

import pandas as pd

from utils.config import get_config, resolve_path
from utils.logger import get_logger

logger = get_logger(__name__)

PathLike = Union[str, Path]


class DatasetLoadError(Exception):
    """Raised when a dataset file cannot be loaded or is fundamentally invalid."""


def _build_alias_lookup(column_aliases: Dict[str, List[str]]) -> Dict[str, str]:
    """
    Flatten the canonical_name -> [aliases] mapping from config.yaml into
    a single lowercase alias -> canonical_name lookup dict for fast renaming.
    """
    lookup: Dict[str, str] = {}
    for canonical, aliases in column_aliases.items():
        # the canonical name itself is always a valid match
        lookup[canonical.lower()] = canonical
        for alias in aliases:
            lookup[str(alias).lower()] = canonical
    return lookup


def standardize_columns(df: pd.DataFrame, column_aliases: Optional[Dict[str, List[str]]] = None) -> pd.DataFrame:
    """
    Rename a DataFrame's columns to canonical names using the alias
    mapping defined in config.yaml (data.column_aliases).

    Unrecognized columns are left untouched (not dropped) so no
    information is silently lost.

    Parameters
    ----------
    df : pd.DataFrame
        Raw input DataFrame.
    column_aliases : dict | None
        Optional override of the alias mapping. Defaults to config.yaml.

    Returns
    -------
    pd.DataFrame
        A copy of `df` with columns renamed to canonical names where a
        match was found.
    """
    if column_aliases is None:
        column_aliases = get_config()["data"]["column_aliases"]

    alias_lookup = _build_alias_lookup(column_aliases)

    rename_map = {}
    for col in df.columns:
        canonical = alias_lookup.get(str(col).strip().lower())
        if canonical and canonical != col:
            rename_map[col] = canonical

    if rename_map:
        logger.info(f"Standardizing columns: {rename_map}")

    return df.rename(columns=rename_map)


def _validate_file_exists(path: Path) -> None:
    if not path.exists():
        raise DatasetLoadError(f"File not found: {path}")
    if not path.is_file():
        raise DatasetLoadError(f"Path is not a file: {path}")
    if path.stat().st_size == 0:
        raise DatasetLoadError(f"File is empty: {path}")


def load_tabular_file(path: PathLike, standardize: bool = True) -> pd.DataFrame:
    """
    Load a CSV or JSON tabular file into a standardized DataFrame.

    Parameters
    ----------
    path : str | Path
        Path to a .csv or .json file (relative paths are resolved
        against the project root).
    standardize : bool
        Whether to rename columns to canonical names via `standardize_columns`.

    Returns
    -------
    pd.DataFrame

    Raises
    ------
    DatasetLoadError
        If the file is missing, empty, unsupported, or unparsable.
    """
    resolved = resolve_path(path)
    _validate_file_exists(resolved)

    suffix = resolved.suffix.lower()
    try:
        if suffix == ".csv":
            df = pd.read_csv(resolved)
        elif suffix == ".json":
            df = pd.read_json(resolved)
        else:
            raise DatasetLoadError(
                f"Unsupported tabular format '{suffix}' for {resolved}. "
                f"Supported formats: .csv, .json"
            )
    except (pd.errors.ParserError, ValueError) as exc:
        raise DatasetLoadError(f"Failed to parse {resolved}: {exc}") from exc

    if df.empty:
        logger.warning(f"Loaded DataFrame from {resolved} is empty (0 rows).")

    if standardize:
        df = standardize_columns(df)

    logger.info(f"Loaded {len(df)} rows x {len(df.columns)} cols from {resolved.name}")
    return df


def load_cyclone_track(path: PathLike, parse_timestamp: bool = True) -> pd.DataFrame:
    """
    Load a cyclone historical-track dataset (CSV/JSON), standardize
    columns, and optionally parse the timestamp column to datetime.

    This is the primary entry point the backend/other developers should
    use for loading historical track data before passing it into the
    inference pipeline.

    Parameters
    ----------
    path : str | Path
        Path to the track file.
    parse_timestamp : bool
        Whether to coerce the `timestamp` column to pandas datetime.

    Returns
    -------
    pd.DataFrame
        Standardized track DataFrame, sorted by timestamp if available.
    """
    df = load_tabular_file(path, standardize=True)

    if parse_timestamp and "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        n_bad = df["timestamp"].isna().sum()
        if n_bad > 0:
            logger.warning(f"{n_bad} row(s) had unparsable timestamps and were set to NaT.")
        df = df.sort_values("timestamp").reset_index(drop=True)

    return df


def load_weather_data(path: PathLike) -> pd.DataFrame:
    """
    Load tabular weather-observation data (SST, humidity, wind, etc).
    Thin wrapper around `load_tabular_file` kept separate for semantic
    clarity and so weather-specific handling can evolve independently
    of track-data handling.
    """
    return load_tabular_file(path, standardize=True)


def list_sample_files(sample_dir: Optional[PathLike] = None) -> Dict[str, List[Path]]:
    """
    Inventory the sample/demo dataset directory, grouped by type.

    Returns
    -------
    dict
        {"images": [...], "tabular": [...], "other": [...]}
    """
    if sample_dir is None:
        sample_dir = get_config()["paths"]["data_sample"]
    resolved = resolve_path(sample_dir)

    image_exts = set(get_config()["data"]["supported_image_formats"])
    tabular_exts = set(get_config()["data"]["supported_tabular_formats"])

    result: Dict[str, List[Path]] = {"images": [], "tabular": [], "other": []}

    if not resolved.exists():
        logger.warning(f"Sample directory does not exist yet: {resolved}")
        return result

    for f in sorted(resolved.rglob("*")):
        if not f.is_file():
            continue
        ext = f.suffix.lower()
        if ext in image_exts:
            result["images"].append(f)
        elif ext in tabular_exts:
            result["tabular"].append(f)
        else:
            result["other"].append(f)

    return result
