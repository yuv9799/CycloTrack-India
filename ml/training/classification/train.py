"""
Training entrypoint for the classification module.

Placeholder for Phase 3+ — will be implemented once the classification model
architecture (see classification/model.py) is in place. Kept separate from the
model/inference code so training-only dependencies (e.g. full datasets,
GPU-heavy loops) never leak into the lightweight inference path.
"""

def train() -> None:
    raise NotImplementedError("Training for 'classification' has not been implemented yet (Phase 1 = data pipeline only).")


if __name__ == "__main__":
    train()
