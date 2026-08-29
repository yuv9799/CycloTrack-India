"""
Central configuration loader for the CycloneAI ML module.

Every other module should obtain settings through `get_config()` /
`get_classes()` rather than reading YAML files directly or hardcoding
values. This keeps the module dataset-agnostic and framework-independent,
per the integration contract with the backend team.
"""

from __future__ import annotations

import os
import functools
from pathlib import Path
from typing import Any, Dict

import yaml

# Project root = one level up from this file (utils/config.py -> ml/)
PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"
DEFAULT_CLASSES_PATH = PROJECT_ROOT / "config" / "classes.yaml"


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data


@functools.lru_cache(maxsize=None)
def get_config(config_path: str | None = None) -> Dict[str, Any]:
    """
    Load (and cache) the main project configuration.

    Parameters
    ----------
    config_path : str | None
        Optional override path to a config.yaml. Defaults to
        `config/config.yaml` at the project root.

    Returns
    -------
    dict
        Parsed configuration.
    """
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    return _load_yaml(path)


@functools.lru_cache(maxsize=None)
def get_classes(classes_path: str | None = None) -> Dict[str, Any]:
    """
    Load (and cache) the configurable class definitions
    (pattern classes, detection classes, intensity categories).
    """
    path = Path(classes_path) if classes_path else DEFAULT_CLASSES_PATH
    return _load_yaml(path)


def resolve_path(relative_path: str | Path) -> Path:
    """
    Resolve a path from config.yaml (which stores paths relative to the
    project root) into an absolute pathlib.Path. Never hardcode paths
    elsewhere in the codebase — always pass them through this function.
    """
    p = Path(relative_path)
    if p.is_absolute():
        return p
    return (PROJECT_ROOT / p).resolve()


def is_demo_mode() -> bool:
    """
    Determine whether the pipeline should run in Demo Mode.

    Priority:
    1. Environment variable DEMO_MODE=true/false (explicit override).
    2. config.yaml -> demo_mode.enabled
    """
    env_val = os.environ.get("DEMO_MODE")
    if env_val is not None:
        return env_val.strip().lower() in {"1", "true", "yes", "on"}

    cfg = get_config()
    return bool(cfg.get("demo_mode", {}).get("enabled", True))


def clear_config_cache() -> None:
    """Clear cached config (useful in tests when config files change)."""
    get_config.cache_clear()
    get_classes.cache_clear()
