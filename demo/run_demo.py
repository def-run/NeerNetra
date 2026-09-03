"""
NeerNetra -- Hackathon Demo Script (Phase 8)
================================================
Run this to demonstrate the full system to judges.
Walks through the 2013 Kedarnath disaster simulation
step by step with formatted output.

Usage:
    1. Start backend:  python -m uvicorn backend.main:app --port 8000
    2. Run demo:       python demo/run_demo.py

The script auto-advances through 7 scenario steps with
pauses for dramatic effect.
"""

import httpx
import time
import sys
import json

BASE = "http://localhost:8000"

DIVIDER = "=" * 70
SUBDIV = "-" * 50


def print_header():
    print()
    print(DIVIDER)
    print("   NeerNetra -- Flash Flood Risk Prediction System")
    print("   LIVE DEMO: 2013 Kedarnath Disaster Simulation")
    print(DIVIDER)
    print()
    print("   Pilot Region: Kedarnath / Mandakini Valley, Uttarakhand")
    print("   Center: 30.735 N, 79.066 E")
    print()


def check_backend():
    print("[1/4] Checking backend server...")
    try:
        r = httpx.get(f"{BASE}/health", timeout=5)
        h = r.json()
        print(f"       Status: {h['status']} | Version: {h['version']}")
        print(f"       Endpoints: {len(h.get('endpoints', {}))} available")
        return True
    except Exception:
        print("       ERROR: Backend not running!")
        print("       Start with: python -m uvicorn backend.main:app --port 8000")
        return False


def show_live_conditions():
    print()
    print("[2/4] Fetching LIVE weather data from Open-Meteo...")
    try:
        r = httpx.get(f"{BASE}/api/risk", params={"lat": 30.735, "lon": 79.067}, timeout=30)
        risk = r.json()
        print(f"       Location: {risk['location']['nearest_station']}")
        print(f"       Risk: {risk['risk_level']} ({(risk['risk_probability']*100):.1f}%)")
        print(f"       Rain 24h: {risk['rainfall']['rain_24h']}mm")
        print(f"       Confidence: {risk['confidence']['confidence_level']}")
        print(f"       Cascade: {risk['cascade']['cascade_risk_level']}")
    except Exception as e:
        print(f"       Error: {e}")


def show_system_overview():
    print()
    print("[3/4] System overview -- monitored locations...")
    try:
        r = httpx.get(f"{BASE}/api/locations")
        locs = r.json()
        print(f"       Monitoring {locs['total']} locations:")
        for loc in locs["locations"]:
            print(f"         {loc['name']:<15} {loc['lat']:.3f}N, {loc['lon']:.3f}E  elev={loc['elevation']}m")
    except Exception as e:
        print(f"       Error: {e}")


def run_simulation():
    print()
    print("[4/4] Starting 2013 Kedarnath Disaster Simulation...")
    print()

    # Start simulation
    try:
        r = httpx.post(f"{BASE}/api/demo/start")
        state = r.json()["state"]
    except Exception as e:
        print(f"       Error starting simulation: {e}")
        return

    # Get scenario overview
    r = httpx.get(f"{BASE}/api/demo/scenario")
    scenario = r.json()
    print(f"       Scenario: {scenario['scenario']}")
    print(f"       Steps: {scenario['total_steps']}")
    print()

    # Walk through each step
    for i in range(scenario["total_steps"]):
        if i > 0:
            r = httpx.post(f"{BASE}/api/demo/advance")
            state = r.json()
        else:
            state = state

        step = state["step"]
        risk = state["risk"]
        rain = state["rainfall"]
        cascade = state["cascade"]
        alerts = state["alerts"]
        prop = state["propagation"]

        # Format output
        print(SUBDIV)
        print(f"  STEP {step['step']}/{scenario['total_steps']-1}: {step['label']}")
        print(f"  {step['elapsed_display']}")
        print(SUBDIV)
        print(f"  {step['description']}")
        print()

        # Risk gauge
        bar_len = 40
        filled = int(risk["probability"] * bar_len)
        bar = "#" * filled + "." * (bar_len - filled)
        print(f"  Risk: [{bar}] {risk['probability']*100:.0f}% {risk['level']}")

        # Rainfall
        print(f"  Rain: 1h={rain['rain_1h']}mm  6h={rain['rain_6h']}mm  24h={rain['rain_24h']}mm  72h={rain['rain_72h']}mm")
        print(f"  Intensity: {rain['rainfall_intensity']}x  |  Cascade: {cascade['cascade_risk_level']}")

        # Propagation
        if prop["active"]:
            print(f"  PROPAGATION: Front at {prop['front']} (ETA: {prop['eta_minutes']}min)")

        # Alerts
        if alerts:
            print()
            for a in alerts:
                prefix = "!!!" if a["type"] in ("FLOOD", "EVACUATION") else " ! "
                print(f"  {prefix} [{a['type']}] {a['message']}")

        # Infrastructure
        damage = state.get("infrastructure_damage", [])
        if damage:
            print(f"\n  Infrastructure damaged: {', '.join(damage)}")

        print()

        # Pause between steps (shorter for demo)
        if i < scenario["total_steps"] - 1:
            for countdown in range(3, 0, -1):
                sys.stdout.write(f"\r  Next step in {countdown}...")
                sys.stdout.flush()
                time.sleep(1)
            print("\r" + " " * 30 + "\r", end="")

    # Stop simulation
    httpx.post(f"{BASE}/api/demo/stop")

    print(DIVIDER)
    print("  SIMULATION COMPLETE")
    print(DIVIDER)


def show_live_lset():
    print()
    print("  BONUS: Live LSET from Kedarnath (current conditions)...")
    print()
    try:
        r = httpx.get(f"{BASE}/api/lset/all", params={"origin": "Kedarnath", "probability": 0.85})
        lset = r.json()
        for l in lset["lset_results"][:5]:
            urgency = l["urgency"]
            mins = l["time_until_lset_minutes"]
            buf = l["safety_buffer_minutes"]
            print(f"    {l['location']:<15} urgency={urgency:<22} LSET={mins}min  buffer={buf}min")
    except Exception as e:
        print(f"    Error: {e}")


def show_infra():
    print()
    print("  BONUS: Infrastructure exposure analysis...")
    print()
    try:
        r = httpx.get(f"{BASE}/api/infrastructure/risk", params={"origin": "Kedarnath", "probability": 0.85})
        infra = r.json()
        print(f"    Bridges at risk: {infra['total_bridges_at_risk']}")
        print(f"    Roads at risk:   {infra['total_road_segments_at_risk']}")
        for b in infra["exposed_bridges"][:3]:
            print(f"      {b['name']:<30} [{b['risk_level']}]  arrival ~{b.get('arrival_minutes', '?')}min")
    except Exception as e:
        print(f"    Error: {e}")


if __name__ == "__main__":
    print_header()

    if not check_backend():
        sys.exit(1)

    show_live_conditions()
    show_system_overview()

    input("\n  Press ENTER to start the 2013 Kedarnath disaster simulation...\n")

    run_simulation()
    show_live_lset()
    show_infra()

    print()
    print(DIVIDER)
    print("   NeerNetra Demo Complete")
    print("   Decision-support prototype -- not a replacement for official warnings.")
    print(DIVIDER)
    print()
