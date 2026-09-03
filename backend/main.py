"""
NeerNetra -- Flash Flood Prediction System (Phase 5)
======================================================
FastAPI application with full service wiring and APScheduler.

Pilot Region: Kedarnath / Mandakini Valley, Uttarakhand
Center: 30.735 N, 79.066 E
"""

import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.api.routes import router as api_router
from backend.api.demo_routes import demo_router


# ---------------------------------------------------------------------------
# Lifespan -- startup / shutdown
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: start scheduler on startup."""
    # Start periodic weather ingestion (if apscheduler available)
    scheduler = None
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from backend.services.ingestion.pipeline import IngestionPipeline

        pipeline = IngestionPipeline()

        scheduler = AsyncIOScheduler()
        scheduler.add_job(
            pipeline.run_weather_ingestion,
            "interval",
            minutes=30,
            id="weather_ingestion",
            name="Weather Data Ingestion",
            next_run_time=None,  # Don't run immediately on startup
        )
        scheduler.start()
        print("[NeerNetra] APScheduler started (weather ingestion every 30 min)")
    except ImportError:
        print("[NeerNetra] APScheduler not installed -- periodic ingestion disabled")
    except Exception as e:
        print(f"[NeerNetra] Scheduler error: {e}")

    print("[NeerNetra] API server ready")
    yield

    # Shutdown
    if scheduler:
        scheduler.shutdown(wait=False)
        print("[NeerNetra] Scheduler stopped")


# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="NeerNetra",
    description=(
        "Explainable, near-real-time flash flood risk prediction system "
        "for hilly regions using multi-source environmental and geospatial data."
    ),
    version="0.2.0",
    lifespan=lifespan,
)

# --- CORS (allow React dev server) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "*",  # For hackathon demo flexibility
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routes ---
app.include_router(api_router, prefix="/api")
app.include_router(demo_router, prefix="/api")


# --- Health Check ---
@app.get("/health", tags=["System"])
async def health_check():
    """Service health check."""
    return {
        "status": "healthy",
        "service": "NeerNetra",
        "version": "0.2.0",
        "phase": "5 - Full Backend",
        "pilot_region": {
            "name": "Kedarnath / Mandakini Valley",
            "lat": 30.735,
            "lon": 79.066,
        },
        "endpoints": {
            "risk": "/api/risk",
            "risk_map": "/api/risk-map",
            "rainfall": "/api/rainfall/current",
            "forecast": "/api/weather/forecast",
            "propagation": "/api/propagation",
            "cascade": "/api/cascade",
            "infrastructure": "/api/infrastructure/risk",
            "lset": "/api/lset",
            "locations": "/api/locations",
            "flood_events": "/api/flood-events",
            "demo_scenario": "/api/demo/scenario",
            "demo_state": "/api/demo/state",
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
