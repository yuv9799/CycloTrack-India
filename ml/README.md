# CycloneAI — ML Module (SIH26070)

**Problem Statement:** AI/ML system for identification, classification, and prediction of
tropical cyclone patterns using multi-source satellite data.
**Organization:** Ministry of Earth Sciences (MoES) · **Domain:** Disaster Management

This repository contains **only the ML module**. It is fully independent of frontend/backend
frameworks — the backend team integrates it with a single import:

```python
from inference.pipeline import CycloneAIPipeline

pipeline = CycloneAIPipeline()
result = pipeline.run_full_analysis(
    image=image_path,
    weather_data=weather_dataframe,
    historical_track=track_dataframe,
)
```

`run_full_analysis` returns a plain, JSON-serializable Python `dict`. No FastAPI, Flask, or
other framework code lives in this repo.

## Status

| Phase | Description | Status |
|---|---|---|
| 1 | Project structure, config system, dataset loader/validator | ✅ Done |
| 2 | Trajectory feature engineering, storm-based splitting | ✅ Done (track data). Image/weather preprocessing still pending. |
| 3 | Cyclone detection model | ⏳ Blocked — needs satellite imagery (none uploaded yet) |
| 4 | Pattern classification model | ⏳ Blocked — needs satellite imagery (none uploaded yet) |
| 5 | Intensity prediction (baseline + LSTM/GRU) | ⏳ Next — data is ready |
| 6 | Trajectory prediction (baseline + LSTM/GRU) | ⏳ Next — data is ready, sequence generator built |
| 7 | Multi-source fusion | ⏳ |
| 8 | Explainability (Grad-CAM, SHAP) | ⏳ |
| 9 | Evaluation reports | ⏳ |
| 10 | Model registry | ⏳ |
| 11 | Unified inference pipeline | ⏳ |
| 13 | Demo mode | ⏳ |
| 15 | Full test suite | ⏳ (26 tests passing so far, Phase 1-2 only) |

## Datasets currently in use

Real NOAA HURDAT2-style Atlantic + Pacific best-track data, uploaded and integrated:

| File | Storms | Date range | Notes |
|---|---|---|---|
| `sample_data/raw/cyclone_tracks_full_1851_2015.csv` | 2,843 | 1851–2015 | Full history. 58% missing pressure (pre-satellite era). |
| `sample_data/raw/cyclone_tracks_2000_2015.csv` | 568 | 2000–2015 | Modern subset, better completeness. **Recommended default for training.** |
| `sample_data/processed/cyclone_tracks_features_2000_2015.csv` | 568 | 2000–2015 | Pre-engineered reference features — used as a golden-file test for `preprocessing/trajectory_preprocessing.py`. |
| `sample_data/sample/tracks/cyclone_demo_sample.csv` | 5 | 2008–2015 | Small demo-mode set. |

**Important:** this is track/tabular data only — no satellite imagery. Phases 3 (detection) and 4
(pattern classification) need image data before they can be built. Also, this data uses the
**Saffir-Simpson** intensity scale (see `config/classes.yaml -> dataset_intensity_categories`),
not the **IMD** scale (`intensity_categories`) implied by the problem statement's North Indian
Ocean / MoES context — the two must not be mixed in one model. If IMD-basin data becomes
available later, retrain against the IMD scale or add a basin-aware scale lookup.


## Project structure

```
ml/
├── config/            # config.yaml (all tunables), classes.yaml (labels)
├── data/              # Data loading abstractions — loader.py, validator.py, splitter.py
├── preprocessing/     # Image / time-series / geospatial preprocessing pipelines
├── detection/         # Cyclone detection model (dataset.py, model.py, evaluate.py, inference.py)
├── classification/    # Pattern classification model
├── intensity/         # Intensity prediction model (baseline + LSTM/GRU)
├── trajectory/        # Trajectory prediction model (baseline + LSTM/GRU)
├── fusion/            # Multimodal feature fusion (image + weather + track)
├── explainability/    # Feature attribution / explanation logic (Grad-CAM, SHAP)
├── utils/             # config.py, logger.py, seed.py, metrics.py, visualization.py
├── training/          # Training scripts, one subfolder per task (kept separate from
│                       # model/inference code so heavy training deps never leak into inference)
├── inference/         # pipeline.py -> CycloneAIPipeline (the backend integration point)
├── notebooks/         # EDA & experiments only — no production code
├── models/            # Saved model weights, one subfolder per task
├── sample_data/       # Demo satellite images, tracks, weather (raw/ processed/ external/ sample/)
├── reports/           # metrics JSON + figures/
└── tests/             # pytest suite
```

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

All tunable values (image size, batch size, learning rate, model architectures, forecast
horizons, column-name aliases, demo-mode behaviour) live in `config/config.yaml`. Class
labels (cyclone pattern stages, intensity category thresholds) live in `config/classes.yaml`
so the dataset's exact label set can change without touching any code.

Demo mode can be toggled without editing files:

```bash
export DEMO_MODE=true   # or false
```

## Dataset loading (Phase 1)

The loader is dataset-agnostic: it accepts CSV/JSON track or weather data with **any**
reasonable column names (`lat`/`Latitude`/`LAT` all map to `latitude`, etc. — see
`config.yaml -> data.column_aliases`) and standardizes them automatically.

```python
from data.loader import load_cyclone_track
from data.validator import validate_track_dataframe, handle_missing_values

df = load_cyclone_track("sample_data/sample/tracks/sample_storm_A.csv")
report = validate_track_dataframe(df, raise_on_missing_required=False)
clean_df = handle_missing_values(df, strategy="interpolate")
```

A sample messy-but-realistic track (`sample_data/sample/tracks/sample_storm_A.csv`) is included
to exercise the loader/validator end-to-end.

## Trajectory preprocessing & splitting (Phase 2)

```python
from data.loader import load_cyclone_track
from data.splitter import split_by_storm
from preprocessing.trajectory_preprocessing import (
    engineer_trajectory_features, create_trajectory_sequences, wind_speed_to_category,
)

df = load_cyclone_track("sample_data/raw/cyclone_tracks_2000_2015.csv")
engineered = engineer_trajectory_features(df)  # adds movement/kinematic features per storm

train_df, val_df, test_df = split_by_storm(engineered)  # storm-level, chronological, no leakage

X, y, meta = create_trajectory_sequences(
    train_df, input_steps=5, forecast_hours=(6, 12, 24, 48),
)  # X: (n, 5, n_features) -> y: (n, 4, [lat, lon])

category = wind_speed_to_category(95)  # "Category 2" (Saffir-Simpson, matches this dataset)
```

`engineer_trajectory_features` was verified row-for-row against the real pre-engineered
reference file (`sample_data/processed/cyclone_tracks_features_2000_2015.csv`) — see
`tests/test_trajectory_preprocessing.py::test_engineered_features_match_real_reference_dataset`.

## Testing

```bash
python -m pytest -v
```

## Coding conventions

- Python 3.11+, type hints everywhere, docstrings on all public classes/functions.
- All paths resolved via `utils/config.py::resolve_path` — never hardcoded.
- `utils/seed.py::set_seed()` called at the start of every training script for
  reproducibility.
- Inference code is kept separate from training code in every task module.
- No FastAPI/Flask imports anywhere under the ML module.
