# NeerNetra — Agent Context & Project State

> **Purpose of this file:** This file is intended to be read by an AI agent at the beginning of a new conversation. It contains the essential context, current progress, and strict execution rules for the NeerNetra flash-flood prediction hackathon project.

## 1. Project Overview
- **Project:** NeerNetra (Water Eye) — an explainable, near-real-time flash flood risk prediction prototype.
- **Target Region:** Kedarnath / Mandakini Valley, Uttarakhand, India.
- **Tech Stack:** React (Vite), FastAPI, PostgreSQL + PostGIS, scikit-learn, GeoPandas, Rasterio, Docker.
- **Goal:** Combine rainfall, terrain, historical floods, and infrastructure data into a time-aware geospatial risk model.

## 2. STRICT Execution Directives (CRITICAL)
The agent **MUST** follow these rules:
1. **Step-by-Step Execution:** Execute only **one phase at a time**.
2. **Mandatory Pause:** After completing the code/setup for a phase, the agent **MUST STOP**.
3. **User Confirmation:** Ask the user: *"Are you ready to proceed to Phase [Next Phase Number]?"*
4. **Do Not Proceed:** Do not write any code for the next phase without explicit user permission.

## 3. Current Project State
- **Completed:** **Phase 1** through **Phase 6** (Frontend).
- **Next Up:** **Phase 7** (Integration & Testing).

### What was built in Phase 1:
- Complete project folder structure (`backend/`, `frontend/`, `ml/`, `geospatial/`, `data/`).
- Root configurations: `docker-compose.yml`, `requirements.txt`, `.gitignore`, `.env.example`, `README.md`.
- PostgreSQL + PostGIS schema (`schema.sql`) and SQLAlchemy ORM models.
- FastAPI backend stubs (`main.py`, `api/routes.py`, `services/`).
- React + Vite frontend initialized with Leaflet map (`FloodMap.jsx`) and a styled dark-theme dashboard.

### What was built in Phase 2:
- `weather_client.py` — Async Open-Meteo API client (current, forecast, historical, multi-location).
- `rainfall_processor.py` — Computes 6 rolling accumulation windows (1h–72h), intensity, and acceleration.
- `synthetic_dem.py` — Generates a synthetic DEM for development/demo terrain features; it is not measured terrain data.
- `dem_processor.py` — Loads/queries GeoTIFF DEMs via Rasterio.
- `feature_extractor.py` — Extracts slope (Horn's method), aspect, TRI, drainage, distance-to-waterbody.
- `road_bridge_loader.py` — GeoPandas loader for road/bridge GeoJSON with spatial queries.
- `coordinate_utils.py` — CRS transformations, haversine distance, UTC alignment.
- `data_seeder.py` — Seeds PostGIS with flood events, landslide data, roads, bridges.
- `pipeline.py` — Orchestrates the full ingestion workflow.
- Seed data: 10 historical flood events, 10 landslide susceptibility records, 7 road segments, 7 bridges.
- **Verified:** Live Open-Meteo API call to Kedarnath returned real data (3555m, 15.4°C).

### What was built in Phase 3:
- `dataset_generator.py` — Generates 5000 realistic labeled samples (15% flood ratio, monsoon-correlated).
- `feature_builder.py` — Assembles 25 features (4 groups) into ML-ready matrices with optional scaling.
- `data_splitter.py` — Temporal train/val/test split (70/15/15) to prevent data leakage.
- `train_model.py` — Full pipeline: trains Logistic Regression + Random Forest + XGBoost.
- `evaluator.py` — Precision, recall, F1, ROC-AUC, PR-AUC, confusion matrix, feature importance.
- `model_registry.py` — Save/load models with metadata via joblib.
- **3 models saved:** `flood_logistic_regression.joblib`, `flood_random_forest.joblib`, `flood_xgboost.joblib`.
- **Top RF features:** rain_24h (0.25), rain_72h (0.15), rain_6h (0.12), rain_1h (0.10).

### What was built in Phase 4:
- `flood_propagation.py` -- Simplified drainage network propagation (terrain-aware, time-stepped).
- `arrival_estimator.py` -- Flood arrival time estimation with confidence rating.
- `cascade_analyzer.py` -- Landslide -> blockage -> flood amplification chain (rule-based).
- `exposure_analyzer.py` -- Road/bridge exposure analysis with priority scoring.
- `lset_calculator.py` -- LSET = Arrival Time - Safety Buffer, with location-specific buffers.
- `confidence.py` -- 5-factor confidence scoring (completeness, recency, calibration, sources, agreement).
- **Verified:** Kedarnath->Rudraprayag propagation: Gaurikund 35min, Sonprayag 50min, Rudraprayag ~4hrs.
- **Verified:** Cascade shows CRITICAL risk at Gaurikund (5 landslide triggers, blockage HIGH).
- **Verified:** 7 bridges + 4 road segments flagged at risk. LSET urgency chain working correctly.

### What was built in Phase 5:
- `prediction_service.py` -- Full orchestrator: weather fetch -> rainfall features -> ML inference -> cascade -> confidence.
- `routes.py` -- 14 live API endpoints replacing all Phase 1 stubs (risk, risk-map, rainfall, forecast, propagation, arrival-time, cascade, infrastructure, LSET, locations).
- `main.py` -- APScheduler integration (30min weather ingestion), CORS, version 0.2.0.
- **Verified:** All 7 tested endpoints returned 200 OK with live Open-Meteo data.
- **Runtime note:** Risk is generated from Open-Meteo plus the configured Random Forest model; propagation is a simplified network estimate and persistence requires the bootstrapped PostgreSQL/PostGIS database.

### What was built in Phase 6:
- `FloodMap.jsx` -- Dark CARTO tiles, risk-colored CircleMarkers, river path, propagation lines, tooltips/popups.
- `Dashboard.jsx` -- Full layout wiring map + 4 panels, scenario controls (origin selector + probability slider), auto-refresh.
- `RiskPanel.jsx` -- Probability gauge, risk level badge, confidence indicator, top risk drivers.
- `RainfallCard.jsx` -- Vertical bar chart for 6 rain windows, weather indicators, forecast values.
- `LSETPanel.jsx` -- Evacuation timeline with urgency-colored items and time countdown.
- `InfraPanel.jsx` -- Bridge/road exposure counts with risk badges.
- `PropagationSlider.jsx` -- Animated time slider with play/pause and affected locations list.
- `App.css` -- Premium dark theme, glassmorphism, Inter + JetBrains Mono, micro-animations.
- `api.js` -- Updated API service matching all 14 backend endpoints.
- **Verified:** Vite compiled with zero errors. Frontend serves at localhost:5173.

## 4. Phase Roadmap (Section 14 of Spec)
* **[COMPLETED] Phase 1:** Problem & Scope Setup (Skeleton, configs, UI/API stubs)
* **[COMPLETED] Phase 2:** Data Pipeline & Geospatial Preparation (Ingest rainfall, process DEM, spatial features)
* **[COMPLETED] Phase 3:** ML Prediction (Feature engineering, train Random Forest, evaluation)
* **[COMPLETED] Phase 4:** Flood Dynamics & Risk Modules (Propagation, arrival-time, cascade, infrastructure exposure, LSET)
* **[COMPLETED] Phase 5:** Backend (FastAPI services, PostgreSQL/PostGIS persistence, APScheduler)
* **[COMPLETED] Phase 6:** Frontend (React map layers, risk panels, time slider)
* **[PENDING] Phase 7:** Integration & Testing (End-to-end pipeline)
* **[PENDING] Phase 8:** Demo Preparation (Simulation mode, demo sequence)

---
**Instruction to Agent:** If you have just read this file in a new conversation, acknowledge the current state and ask the user if they are ready to begin **Phase 7**.
