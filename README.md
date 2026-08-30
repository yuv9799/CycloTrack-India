# 🌪️ CycloneAI — AI-Powered Tropical Cyclone Intelligence System

**Smart India Hackathon 2026 · Problem Statement SIH26070**

> Identification, Classification, and Prediction of Tropical Cyclone Patterns using Multi-Source Satellite Data

| | |
|---|---|
| **Problem Code** | SIH26070 |
| **Organization** | Ministry of Earth Sciences (MoES) |
| **Category** | Software |
| **Domain** | Disaster Management |
| **Team** | NEXUS |

---

## 📖 Table of Contents

1. [Overview](#-overview)
2. [System Architecture](#-system-architecture)
3. [Technology Stack](#-technology-stack)
4. [Project Structure](#-project-structure)
5. [Core Features](#-core-features)
6. [User Flow](#-user-flow)
7. [ML Pipeline](#-ml-pipeline)
8. [API Reference](#-api-reference)
9. [Emergency Response Features](#-emergency-response-features)
10. [Database Schema](#-database-schema)
11. [Getting Started](#-getting-started)
12. [Environment Variables](#-environment-variables)
13. [Docker Deployment](#-docker-deployment)
14. [Demo Mode vs Real ML Mode](#-demo-mode-vs-real-ml-mode)
15. [Model Performance](#-model-performance)
16. [Report Generation](#-report-generation)
17. [Security](#-security)
18. [Roadmap](#-roadmap)
19. [Team](#-team)
20. [Disclaimer](#-disclaimer)

---

## 🌊 Overview

**CycloneAI** is a full-stack, AI/ML-driven disaster intelligence platform built for SIH 2026 under the Ministry of Earth Sciences. It ingests multi-source satellite, meteorological, and historical data to:

- **Detect** tropical cyclones in satellite imagery
- **Classify** cyclone patterns (Developing, Mature, Spiral, Symmetric, Weak, Dissipating)
- **Predict** intensity evolution (wind speed, pressure, category)
- **Forecast** future trajectory (+6h, +12h, +24h, +48h)
- **Visualize** results on an interactive India / Indian Ocean map
- **Explain** predictions through an explainable-AI dashboard
- **Archive** every analysis for historical comparison and reporting

The system is designed to run entirely in a **Demo Mode** using realistic synthetic data (so judges can evaluate the full workflow without external APIs), while remaining architecturally ready to swap in trained models and live satellite feeds for a **Real ML Mode**.

---

## 🏗️ System Architecture

```
                    MULTI-SOURCE DATA
                           |
        -----------------------------------------
        |                  |                    |
   Satellite Data      Weather Data       Historical Data
        |                  |                    |
        -----------------------------------------
                           |
                    DATA INGESTION
                           |
                    DATA PREPROCESSING
                           |
        ------------------------------------------
        |                   |                    |
   Image Pipeline      Time-Series Pipeline   Geospatial Pipeline
        |                   |                    |
        ------------------------------------------
                           |
                      ML ENGINE
                           |
        ------------------------------------------------
        |                  |              |             |
   Cyclone Detection   Classification   Intensity    Trajectory
        |                  |              |             |
        ------------------------------------------------
                           |
                    PREDICTION API
                           |
              BACKEND + DATABASE + STORAGE
                           |
                       FRONTEND
                           |
          DASHBOARD + MAP + ANALYTICS + REPORTS
```

Each stage is a decoupled module communicating through well-defined interfaces, so any component (e.g. a baseline XGBoost intensity model) can be swapped for an advanced one (e.g. an LSTM) without touching the rest of the system.

---

## 🧰 Technology Stack

### Frontend
| Tool | Purpose |
|---|---|
| Next.js + React + TypeScript | App framework |
| Tailwind CSS + shadcn/ui | Design system |
| Framer Motion | Animation |
| Recharts / Chart.js | Data visualization |
| Leaflet / Mapbox | Interactive geospatial map |
| TanStack Query | Server-state management |

### Backend
| Tool | Purpose |
|---|---|
| FastAPI | REST API framework |
| Pydantic | Schema validation |
| SQLAlchemy | ORM |
| JWT (python-jose / passlib) | Authentication |

### ML / Data Science
| Tool | Purpose |
|---|---|
| PyTorch / TensorFlow-Keras | Deep learning (detection, classification) |
| Scikit-learn, XGBoost | Baseline intensity & trajectory models |
| Pandas, NumPy | Data processing |
| OpenCV, Rasterio | Satellite image processing |
| Xarray | NetCDF / gridded meteorological data |
| GeoPandas | Geospatial feature engineering |

### Database & Storage
- **PostgreSQL** with **PostGIS** for geospatial queries
- Local filesystem storage in development, structured for AWS S3 migration

### DevOps
- **Docker** + **Docker Compose** with separate `frontend`, `backend`, and `ml` services

---

## 📂 Project Structure

```
cyclone-ai/
│
├── frontend/
│   ├── app/                  # Next.js app router pages
│   ├── components/           # Reusable UI components
│   ├── features/             # Feature-scoped modules (analysis, map, history...)
│   ├── lib/                  # Utilities, constants
│   ├── hooks/                # Custom React hooks
│   ├── services/             # API client layer
│   ├── types/                # TypeScript types/interfaces
│   └── public/                # Static assets
│
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI entrypoint
│   │   ├── core/              # Config, security, JWT
│   │   ├── api/                # Route definitions (v1 endpoints)
│   │   ├── models/            # SQLAlchemy ORM models
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   ├── services/            # Business logic / orchestration layer
│   │   ├── repositories/        # DB access layer
│   │   ├── database/            # Session, migrations
│   │   └── utils/                # Shared helpers
│   └── requirements.txt
│
├── ml/
│   ├── data/                  # Data loading abstractions
│   ├── preprocessing/          # Image / time-series / geospatial pipelines
│   ├── detection/               # Cyclone detection model
│   ├── classification/          # Pattern classification model
│   ├── intensity/                # Intensity prediction model
│   ├── trajectory/                # Trajectory prediction model
│   ├── explainability/            # Feature attribution / explanation logic
│   ├── models/                     # Saved model weights
│   ├── training/                    # Training scripts
│   ├── inference/                    # Inference service wrappers
│   └── notebooks/                     # Experimentation notebooks
│
├── sample_data/                 # Demo satellite images, tracks, weather CSVs
├── docker/                      # Dockerfiles per service
├── docs/                        # Architecture docs, diagrams
├── docker-compose.yml
└── README.md
```

---

## ✨ Core Features

- 🌍 **Multi-Source Data Integration** — satellite imagery, weather data, historical cyclone tracks
- 🛰️ **AI Cyclone Detection** — CNN-based binary classifier (cyclone / no cyclone)
- 🔄 **Pattern Classification** — Developing, Mature, Spiral, Symmetric, Weak, Dissipating
- 📈 **Intensity Forecasting** — wind speed, central pressure, intensity category
- 🧭 **Trajectory Prediction** — sequence modeling for +6h/+12h/+24h/+48h forecasts
- 🧠 **Explainable AI** — top contributing features behind every prediction
- 🗺️ **Real-Time Map Visualization** — India, Bay of Bengal, Arabian Sea, Indian Ocean
- 📚 **Historical Cyclone Database** — searchable archive with comparisons
- 📄 **PDF Report Generation** — full scientific report per analysis
- 🔐 **Role-Based Access** — Admin, Researcher, User
- 🧪 **Demo Mode** — fully functional without live external APIs
- 💬 **CycloBot AI Assistant** — a genuine AI chatbot (Claude, via `backend/`) embedded on every page that can answer open-ended questions about cyclones and this project, not just fixed FAQ phrases. See [`backend/README.md`](backend/README.md) to run it; the widget falls back to a small offline knowledge base if the AI backend isn't running.

---

## 🧭 User Flow

```
Landing Page → Login/Register → Dashboard
                                     │
                    ┌────────────────┴────────────────┐
                    ▼                                  ▼
             New Analysis                       Historical Data
                    │
        Select Data Source → Select Region → Select Date/Time
                    │
              Upload Data → Select Analysis Options
                    │
              Run AI Analysis
                    │
        Detection → Classification → Intensity → Trajectory
                    │
              Results Dashboard
                    │
        ┌───────────┼────────────┐
        ▼           ▼            ▼
       Map        Charts       Report
                    │
         Save to Prediction History
```

---

## 🤖 ML Pipeline

### 1. Data Ingestion (`DataSource` abstraction)
```python
load_satellite_data()
load_weather_data()
load_historical_data()
load_demo_data()
```
Gracefully falls back to demo/synthetic data if a live source is unavailable.

### 2. Preprocessing
- **Image:** resize → normalize → denoise → cloud enhancement → channel conversion → augmentation
- **Time-Series:** missing-value handling → sorting → normalization → lag features → sequence generation
- **Geospatial:** coordinate validation → conversion → spatial features → movement vectors → distance/direction

### 3. Cyclone Detection
- Transfer learning (EfficientNet / ResNet / MobileNet) → global pooling → dense layers → binary output
- Output: `cyclone_detected`, `confidence`, `bounding_region`, `center_lat/lon`

### 4. Pattern Classification
- Fine-tuned CNN multiclass classifier over configurable pattern classes
- Output: `predicted_class`, `confidence`, per-class `probabilities`

### 5. Intensity Prediction
- Baseline: Random Forest / XGBoost on SST, pressure, wind, humidity, lat/lon, historical intensity
- Advanced: LSTM/GRU sequence regression
- Output: wind speed, central pressure, intensity category

### 6. Trajectory Prediction
- Baseline: XGBoost regression on historical track sequences
- Advanced: LSTM/GRU or Transformer sequence-to-sequence model
- Output: forecast coordinates at +6h/+12h/+24h/+48h

### 7. Multi-Modal Fusion (Phase 3)
```
Satellite Image → CNN Feature Extractor ─┐
Weather Features ────────────────────────┼─→ Feature Fusion → Prediction
Historical Track ─────────────────────────┘
```

Every prediction returns `confidence_score`, `model_name`, `model_version`, and `prediction_timestamp` for full traceability.

---

## 🔌 API Reference

Base path: `/api/v1`

| Group | Endpoints |
|---|---|
| **Auth** | `POST /auth/register` · `POST /auth/login` · `GET /auth/me` |
| **Analysis** | `POST /analysis/upload` · `POST /analysis/run` · `GET /analysis/{id}` · `GET /analysis/{id}/status` |
| **Predictions** | `POST /predictions/detect` · `POST /predictions/classify` · `POST /predictions/intensity` · `POST /predictions/trajectory` · `POST /predictions/full-analysis` |
| **History** | `GET /history` · `GET /history/{id}` · `DELETE /history/{id}` |
| **Cyclones / Map** | `GET /cyclones` · `GET /map` |
| **Models** | `GET /models` (performance metrics) |
| **Reports** | `POST /reports/{analysis_id}` (PDF generation) |

### Sample `full-analysis` response
```json
{
  "analysis_id": "ANL-2026-001",
  "status": "completed",
  "detection": { "cyclone_detected": true, "confidence": 0.96 },
  "classification": { "pattern": "Mature Cyclone", "confidence": 0.93 },
  "intensity": { "wind_speed": 135, "pressure": 945, "category": "Severe Cyclonic Storm" },
  "location": { "latitude": 16.5, "longitude": 87.3 },
  "trajectory": [
    { "forecast": "+6h", "latitude": 16.8, "longitude": 87.0 },
    { "forecast": "+12h", "latitude": 17.2, "longitude": 86.5 },
    { "forecast": "+24h", "latitude": 18.1, "longitude": 85.8 }
  ],
  "model": { "name": "CycloneAI", "version": "1.0" }
}
```

---

## 🚨 Emergency Response Features

The static frontend now ships disaster-response tooling alongside the cyclone
tracking dashboard:

- **Report / Request Help** (`frontend/report.html`) — a validated emergency
  form (name, mobile, state, district, village/city, current location, numbers
  of people/children/elderly, emergency type, description, optional photo, and
  consent). A prominent **Submit Emergency Request** button is linked from the
  hero and the navbar on every page.
- **`POST /api/help-requests`** — the FastAPI backend validates and stores
  submissions in a JSON-lines file (default `backend/data/help_requests.jsonl`,
  override with `HELP_REQUESTS_FILE`). On GitHub Pages there is no live backend,
  so the form falls back to storing the request in the browser's `localStorage`
  and surfaces a clear notice. Personal details are never exposed through a
  public route (`GET /api/help-requests` returns only aggregate counts).
- **Cyclone Helplines** (`frontend/helplines.html`) — clearly labelled national
  numbers (`112`, `108`, `101`, `1078`) with tap-to-call `tel:` links, an
  extended disaster-response table, and a disclaimer directing people to verify
  local/state numbers and follow official IMD/NDMA advisories.
- **Quick-action cards** on the homepage — Request Rescue, Medical Help, Find
  Shelter, Report Damage, and Emergency Helplines — which pre-fill the help form.
- **Accessibility** — labelled form fields, ARIA live regions, visible keyboard
  focus, a skip-to-content link, high-contrast emergency styling, responsive
  layouts, and `prefers-reduced-motion` support.

---

## 🗄️ Database Schema

| Table | Key Columns |
|---|---|
| `users` | id, name, email, hashed_password, role, created_at |
| `analyses` | id, user_id, region, latitude, longitude, data_source, status, created_at |
| `uploaded_files` | id, analysis_id, file_name, file_type, file_path, created_at |
| `predictions` | id, analysis_id, cyclone_detected, pattern_class, classification_confidence, wind_speed, pressure, intensity_category, created_at |
| `trajectories` | id, prediction_id, forecast_time, latitude, longitude |
| `model_metrics` | id, model_name, model_version, accuracy, precision, recall, f1_score, created_at |

PostGIS geometry columns are used on `analyses` and `trajectories` for spatial querying (e.g. cyclones within a bounding box).

Emergency help requests submitted via `POST /api/help-requests` are stored in a
JSON-lines file (`backend/data/help_requests.jsonl`, ignored by git) rather than
the relational database, so a deployed static frontend + minimal FastAPI service
can accept them without provisioning PostgreSQL.

---

## 🚀 Getting Started

### Prerequisites
- Node.js ≥ 18
- Python ≥ 3.10
- PostgreSQL ≥ 14 (with PostGIS)
- Docker & Docker Compose (recommended)

### 1. Clone & configure
```bash
git clone https://github.com/team-nexus/cyclone-ai.git
cd cyclone-ai
cp .env.example .env   # fill in secrets — see Environment Variables
```

### 2. Backend
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head          # run DB migrations
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend
```bash
cd frontend
npm install
npm run dev                   # http://localhost:3000
```

### 4. ML Service (optional, standalone inference)
```bash
cd ml
pip install -r requirements.txt
python inference/serve.py
```

### 5. Verify
- Frontend: `http://localhost:3000`
- Backend docs (Swagger): `http://localhost:8000/docs`
- Health check: `GET /api/v1/health`

---

## 🔑 Environment Variables

```env
# Backend
DATABASE_URL=postgresql://user:password@localhost:5432/cyclone_ai
SECRET_KEY=change-me
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60
STORAGE_BACKEND=local          # local | s3
S3_BUCKET_NAME=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
CORS_ORIGINS=http://localhost:3000

# Frontend
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_MAP_TOKEN=

# ML
MODEL_MODE=demo                # demo | real
MODEL_REGISTRY_PATH=./ml/models
```

> Never commit `.env` files. Secrets, API keys, and DB credentials must always be injected via environment variables.

---

## 🐳 Docker Deployment

```bash
docker compose up --build
```

This spins up:
- `frontend` (Next.js, port 3000)
- `backend` (FastAPI, port 8000)
- `db` (PostgreSQL + PostGIS, port 5432)
- `ml` (inference service, internal network)

Each service has its own Dockerfile under `docker/`, and `docker-compose.yml` wires them together with shared volumes for `sample_data/` and model artifacts.

---

## 🧪 Demo Mode vs Real ML Mode

CycloneAI ships with a fully functional **Demo Mode** so the entire workflow — upload, detect, classify, predict, visualize, report — works end-to-end without any live satellite API or trained model.

| | Demo Mode | Real ML Mode |
|---|---|---|
| Satellite data | 5–10 curated sample images | Live satellite feed / uploaded imagery |
| Historical tracks | Pre-loaded sample cyclone events (name, date, region, coordinates, wind speed, pressure, intensity, pattern, track) | IMD/JTWC historical database |
| Models | Deterministic realistic synthetic outputs | Trained CNN/XGBoost/LSTM checkpoints |
| Switch | `MODEL_MODE=demo` | `MODEL_MODE=real` |

The mode is controlled entirely by configuration — no code changes required to switch, since inference calls go through a common `ml/inference` service interface.

---

## 📊 Model Performance

A dedicated **Model Performance** page reports (using realistic placeholder metrics until real training completes):

- **Detection:** Accuracy, Precision, Recall, F1 Score
- **Classification:** Accuracy, Confusion Matrix
- **Trajectory:** MAE, RMSE, Distance Error (km)

---

## 📄 Report Generation

Each completed analysis can be exported as a PDF containing:

1. Detection Result
2. Pattern Classification
3. Intensity Prediction
4. Current Location
5. Predicted Trajectory
6. Risk Assessment
7. Model Confidence
8. Charts
9. AI Explanation
10. Disclaimer

---

## 🔒 Security

- JWT-based authentication with bcrypt password hashing
- Role-based authorization (Admin / Researcher / User)
- Strict input & file-type/size validation
- CORS configuration restricted to known origins
- All secrets managed via environment variables — never hardcoded

---

## 🗺️ Roadmap

- [x] Phase 1 — Baseline detection, classification, intensity, trajectory models
- [ ] Phase 2 — Advanced CNN/EfficientNet + LSTM/Transformer models
- [ ] Phase 3 — Multi-modal fusion (image + weather + historical track)
- [ ] Integration with live IMD/INSAT satellite feeds
- [ ] Mobile-responsive PWA support

---

## 👥 Team

**SIH 2026 — Team NEXUS**

| Role | Name |
|---|---|
| Team Lead | _TBD_ |
| ML/AI Engineer | _TBD_ |
| Backend Engineer | _TBD_ |
| Frontend Engineer | _TBD_ |
| Geospatial/Data Engineer | _TBD_ |
| UI/UX Designer | _TBD_ |

*(Replace with actual team member names before submission)*

---

## ⚠️ Disclaimer

CycloneAI is a research and decision-support prototype built for Smart India Hackathon 2026. All predictions are **AI-generated for research and decision-support purposes only** and must not be used as the sole basis for official disaster-response decisions. Always defer to official IMD/MoES advisories for real-world cyclone warnings.

---

<p align="center">Built for <b>Smart India Hackathon 2026</b> · Problem Statement <b>SIH26070</b> · Ministry of Earth Sciences</p>
