"""
NeerNetra -- Demo API Routes (Phase 8)
=========================================
Endpoints for hackathon demo simulation.
Controls the 2013 Kedarnath disaster replay.
"""

from fastapi import APIRouter, Query
from backend.services.simulation.demo_simulator import DemoSimulator

demo_router = APIRouter(prefix="/demo", tags=["Demo"])

# Shared simulator instance
simulator = DemoSimulator()


@demo_router.post("/start")
async def start_demo():
    """Start the Kedarnath 2013 disaster simulation."""
    simulator.start()
    return {
        "message": "Demo simulation started: Kedarnath 2013 Disaster",
        "state": simulator.get_current_state(),
    }


@demo_router.post("/stop")
async def stop_demo():
    """Stop and reset the simulation."""
    simulator.stop()
    return {"message": "Demo simulation stopped and reset."}


@demo_router.post("/advance")
async def advance_demo():
    """Advance to the next simulation step."""
    state = simulator.advance()
    return state


@demo_router.post("/step/{step_number}")
async def go_to_step(step_number: int):
    """Jump to a specific simulation step (0-6)."""
    state = simulator.go_to_step(step_number)
    return state


@demo_router.get("/state")
async def get_demo_state():
    """Get the current simulation state."""
    return simulator.get_current_state()


@demo_router.get("/scenario")
async def get_scenario_info():
    """Get full scenario timeline overview."""
    steps = []
    for s in simulator.scenario:
        steps.append({
            "step": s["step"],
            "label": s["label"],
            "description": s["description"],
            "elapsed_display": s["elapsed_display"],
            "risk_level": s["risk_level"],
            "rain_24h": s["rain_24h"],
        })
    return {
        "scenario": "Kedarnath 2013 Disaster",
        "total_steps": len(steps),
        "steps": steps,
    }
