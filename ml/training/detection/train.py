"""
Training entrypoint for the detection module.

Placeholder for Phase 3+ — will be implemented once the detection model
architecture (see detection/model.py) is in place. Kept separate from the
model/inference code so training-only dependencies (e.g. full datasets,
GPU-heavy loops) never leak into the lightweight inference path.
"""

def train() -> None:
    raise NotImplementedError("Training for 'detection' has not been implemented yet (Phase 1 = data pipeline only).")


if __name__ == "__main__":
    train()
