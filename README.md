# NeerNetra — Flash Flood Prediction System for Hilly Regions

> **An explainable, near-real-time flash flood risk prediction prototype for hilly regions using multi-source environmental and geospatial data.**

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green?logo=fastapi)
![React](https://img.shields.io/badge/React-18+-61DAFB?logo=react)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-336791?logo=postgresql)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)

---

## Overview

NeerNetra (नीरनेत्र — "Water Eye") is a decision-support and early-warning prototype that combines rainfall, terrain, historical flood information, and infrastructure data to:

1. **Predict** location-specific flood risk using terrain-aware ML models
2. **Propagate** estimated flood extent across a spatial grid over time
3. **Estimate** flood arrival times for downstream locations
4. **Detect** basic landslide → blockage → flood cascade scenarios
5. **Identify** exposed roads and bridges
6. **Calculate** Estimated Last Safe Departure Time (LSET)
7. **Communicate** prediction uncertainty and confidence

### Pilot Region

**Kedarnath / Mandakini Valley, Uttarakhand, India**
- Center: 30.735°N, 79.066°E
- One of India's most flash-flood-prone hilly regions (2013 Kedarnath disaster)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React (Vite) |
| Backend | FastAPI (Python) |
| ML | scikit-learn / Random Forest / XGBoost |
| Database | PostgreSQL + PostGIS |
| Data Processing | Pandas + NumPy |
| Geospatial | GeoPandas + Rasterio |
| Scheduling | APScheduler |
| Maps | Leaflet / MapLibre GL JS |
| Deployment | Docker |

---

## Complete Setup & Execution Guide

Follow these steps to run the complete NeerNetra flash flood prediction system on your local machine.

### Prerequisites
- **Python 3.11+**
- **Node.js 18+** (with npm)
- **Git**

### Step 1: Clone the Repository
```bash
git clone https://github.com/your-team/neernetra.git
cd neernetra
```

### Step 2: Install Backend Dependencies & Start Server
The backend is a FastAPI application that orchestrates weather ingestion, ML inference, and flood dynamics.

Open a terminal in the root directory of the project:
```bash
# Optional: Create a virtual environment
python -m venv venv
# Windows: venv\Scripts\activate
# Mac/Linux: source venv/bin/activate

# Install dependencies (from root directory)
pip install -r requirements.txt

# Start the FastAPI server (it will run on http://localhost:8000)
# Make sure you are in the NeerNetra root directory when running this:
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
You should see the server start and APScheduler initializing for periodic weather ingestion.

### Step 3: Install Frontend Dependencies & Start Dashboard
The frontend is a React application built with Vite that provides the interactive dashboard.

Open a **new, separate terminal** in the root directory:
```bash
# Navigate to the frontend directory
cd frontend

# Install Node dependencies
npm install

# Start the Vite development server
npm run dev
```

### Step 4: Access the Application
- **Dashboard UI**: Open your browser and navigate to `http://localhost:5173`
- **Backend API Docs**: Open your browser and navigate to `http://localhost:8000/docs` to see the interactive Swagger UI for all API endpoints.

---

## Project Structure

```
NeerNetra/
├── backend/          # FastAPI backend
├── frontend/         # React + Vite frontend
├── ml/               # ML training & models
├── geospatial/       # Terrain & spatial analysis
├── data/             # Raw & processed datasets
├── notebooks/        # Jupyter notebooks
├── docker/           # Dockerfiles
├── docs/             # Documentation
└── docker-compose.yml
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/risk` | Current flood risk for a location |
| GET | `/api/rainfall/history` | Historical rainfall data |
| GET | `/api/weather/forecast` | Weather forecast |
| GET | `/api/risk-map` | Spatial risk grid |
| GET | `/api/flood-events` | Historical flood events |
| GET | `/api/propagation` | Flood propagation results |
| GET | `/api/infrastructure/risk` | Road/bridge risk |
| GET | `/health` | Service health check |

---

## Disclaimer

> This is a **decision-support and early-warning prototype**, not an authoritative replacement for government flood warnings. All predictions, propagation estimates, arrival times, LSET values, and confidence indicators are estimates and must be treated accordingly.

---

## License

MIT License — See [LICENSE](LICENSE) for details.
