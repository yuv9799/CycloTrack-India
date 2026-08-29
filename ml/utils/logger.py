"""
Central logging factory for the CycloneAI ML module.

Usage
-----
    from utils.logger import get_logger
    logger = get_logger(__name__)
    logger.info("Loaded 1204 rows")
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

_CONFIGURED_LOGGERS: set[str] = set()


def get_logger(name: str, log_file: Optional[str] = None, level: Optional[str] = None) -> logging.Logger:
    """
    Return a configured logger. Safe to call repeatedly with the same
    name (handlers are attached only once per logger).

    Parameters
    ----------
    name : str
        Usually `__name__` of the calling module.
    log_file : str | None
        Optional path override. Defaults to config.yaml -> logging.log_file.
    level : str | None
        Optional level override (e.g. "DEBUG"). Defaults to config.yaml -> logging.level.
    """
    logger = logging.getLogger(name)

    if name in _CONFIGURED_LOGGERS:
        return logger

    # Resolve settings from config, but never fail hard if config is missing
    # (logger must work even before config files exist, e.g. during setup).
    log_level_str = level
    write_to_file = True
    resolved_log_file = log_file

    try:
        from utils.config import get_config, resolve_path

        cfg = get_config()
        log_cfg = cfg.get("logging", {})
        log_level_str = log_level_str or log_cfg.get("level", "INFO")
        write_to_file = log_cfg.get("log_to_file", True)
        resolved_log_file = resolved_log_file or log_cfg.get("log_file", "reports/logs/cyclone_ai.log")
        resolved_log_file = str(resolve_path(resolved_log_file))
    except Exception:
        log_level_str = log_level_str or "INFO"
        write_to_file = False

    level_value = getattr(logging, log_level_str.upper(), logging.INFO)
    logger.setLevel(level_value)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if write_to_file and resolved_log_file:
        try:
            log_path = Path(resolved_log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_path, encoding="utf-8")
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except OSError:
            # If the filesystem is read-only or path is unavailable, fall back
            # to console-only logging rather than crashing the pipeline.
            pass

    logger.propagate = False
    _CONFIGURED_LOGGERS.add(name)
    return logger
