"""
Training entrypoint for the intensity module.

Placeholder for Phase 3+ — will be implemented once the intensity model
architecture (see intensity/model.py) is in place. Kept separate from the
model/inference code so training-only dependencies (e.g. full datasets,
GPU-heavy loops) never leak into the lightweight inference path.
"""

def train() -> None:
    raise NotImplementedError("Training for 'intensity' has not been implemented yet (Phase 1 = data pipeline only).")


if __name__ == "__main__":
    train()
