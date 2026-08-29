"""
Reproducibility helper.

Call `set_seed()` once at the start of any training or inference script
so that results are reproducible across runs (Coding Requirement #7).
"""

from __future__ import annotations

import os
import random
from typing import Optional

import numpy as np


def set_seed(seed: int = 42, deterministic_torch: bool = True) -> None:
    """
    Seed Python's `random`, NumPy, and (if installed) PyTorch.

    Parameters
    ----------
    seed : int
        Seed value. Defaults to 42, matching config.yaml -> training.random_seed.
    deterministic_torch : bool
        If True and torch is available, forces deterministic cuDNN behaviour.
        This can slow down training slightly but removes run-to-run variance.
    """
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)

    try:
        import torch

        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        if deterministic_torch:
            torch.backends.cudnn.deterministic = True
            torch.backends.cudnn.benchmark = False
    except ImportError:
        # torch is optional at this stage of the pipeline (Phase 1 doesn't need it)
        pass


def get_seed_from_config(default: int = 42) -> int:
    """Fetch the configured random seed, falling back to `default`."""
    try:
        from utils.config import get_config

        return int(get_config().get("training", {}).get("random_seed", default))
    except Exception:
        return default
