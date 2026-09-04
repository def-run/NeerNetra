"""
NeerNetra -- Phase 7: End-to-End Integration Tests
=====================================================
Validates the complete pipeline from data ingestion through
API response. Tests run against the live backend server.

Usage:
    1. Start backend: python -m uvicorn backend.main:app --port 8000
    2. Run tests:     python tests/test_integration.py

All tests are self-contained and use ASCII-only output for Windows.
"""

import sys
import os
import json
import time
import traceback
from datetime import datetime

# This file is an executable smoke-test script, not a pytest fixture module.
__test__ = False

# Add project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# =========================================================================
# Test Tracking
# =========================================================================
RESULTS = {"passed": 0, "failed": 0, "errors": []}

def test(name, func):
    """Run a single test with error handling."""
    try:
        func()
        RESULTS["passed"] += 1
        print(f"  [PASS] {name}")
    except AssertionError as e:
        RESULTS["failed"] += 1
        RESULTS["errors"].append(f"{name}: ASSERT {e}")
        print(f"  [FAIL] {name}: {e}")
    except Exception as e:
        RESULTS["failed"] += 1
        RESULTS["errors"].append(f"{name}: ERROR {e}")
        print(f"  [ERR ] {name}: {e}")


# =========================================================================
# SECTION 1: Unit Tests (no server required)
# =========================================================================
def run_unit_tests():
    print("\n" + "=" * 60)
    print("  UNIT TESTS (no server required)")
    print("=" * 60)

    # --- Weather Client ---
    def test_weather_client_init():
        from backend.services.ingestion.weather_client import WeatherClient
        client = WeatherClient()
        assert client is not None
        assert hasattr(client, 'fetch_current_and_forecast')
        assert hasattr(client, 'fetch_recent_rainfall')
    test("WeatherClient initializes", test_weather_client_init)

    # --- Rainfall Processor ---
    def test_rainfall_processor():
        from backend.services.ingestion.rainfall_processor import RainfallProcessor
        from datetime import datetime, timedelta, timezone
        proc = RainfallProcessor()

        # Build hourly records as the processor expects (list of dicts)
        now = datetime.now(timezone.utc)
        hourly = []
        for i in range(72):
            t = now - timedelta(hours=71 - i)
            hourly.append({"time": t.isoformat(), "precipitation": 0.5})

        features = proc.compute_rainfall_features(hourly)

        assert "rain_1h" in features
        assert "rain_6h" in features
        assert "rain_24h" in features
        assert "rain_72h" in features
        assert features["rain_1h"] == 0.5
        assert abs(features["rain_6h"] - 3.0) < 0.01
        assert abs(features["rain_24h"] - 12.0) < 0.01
        assert abs(features["rain_72h"] - 36.0) < 0.01
    test("RainfallProcessor computes correct windows", test_rainfall_processor)

    # --- Flood Propagation ---
    def test_propagation_engine():
        from backend.services.propagation.flood_propagation import FloodPropagationEngine
        engine = FloodPropagationEngine()

        result = engine.propagate("Kedarnath", origin_probability=0.9, rainfall_intensity=1.5)
        assert "error" not in result
        assert result["total_steps"] > 0
        assert result["total_locations_affected"] > 0

        # Verify downstream order
        steps = result["time_steps"]
        first_names = []
        for s in steps:
            for loc in s.get("affected_locations", []):
                if loc["name"] not in first_names:
                    first_names.append(loc["name"])
        # Kedarnath itself should not be in affected (it's the origin)
        assert "Gaurikund" in first_names, f"Gaurikund not in {first_names}"
    test("FloodPropagation produces valid downstream chain", test_propagation_engine)

    # --- Propagation with invalid origin ---
    def test_propagation_invalid():
        from backend.services.propagation.flood_propagation import FloodPropagationEngine
        engine = FloodPropagationEngine()
        result = engine.propagate("InvalidCity", origin_probability=0.9)
        assert "error" in result
    test("FloodPropagation handles invalid origin", test_propagation_invalid)

    # --- Arrival Time ---
    def test_arrival_time():
        from backend.services.arrival_time.arrival_estimator import ArrivalTimeEstimator
        est = ArrivalTimeEstimator()

        result = est.estimate("Kedarnath", "Sonprayag", origin_probability=0.85)
        assert "estimated_arrival_time" in result
        assert result["travel_time_minutes"] > 0
        assert result["confidence"] in ("HIGH", "MEDIUM", "LOW")
    test("ArrivalTimeEstimator Kedarnath->Sonprayag", test_arrival_time)

    # --- Arrival Time for all downstream ---
    def test_arrival_all():
        from backend.services.arrival_time.arrival_estimator import ArrivalTimeEstimator
        est = ArrivalTimeEstimator()

        results = est.estimate_for_all_downstream("Kedarnath", origin_probability=0.85)
        assert len(results) > 3, f"Expected > 3 downstream, got {len(results)}"
    test("ArrivalTimeEstimator all downstream locations", test_arrival_all)

    # --- Cascade Analyzer ---
    def test_cascade():
        from backend.services.cascade.cascade_analyzer import CascadeAnalyzer
        analyzer = CascadeAnalyzer()

        # High-risk scenario
        result = analyzer.analyze(
            location_name="Gaurikund",
            rain_6h=80, rain_24h=200,
            slope=30, landslide_susceptibility=0.85,
            elevation=1982, distance_to_waterbody=0.1,
        )
        assert result["cascade_risk_level"] in ("HIGH", "CRITICAL")
        assert result["cascade_risk_score"] > 0.5

        # Low-risk scenario
        result_low = analyzer.analyze(
            location_name="Rudraprayag",
            rain_6h=5, rain_24h=10,
            slope=8, landslide_susceptibility=0.3,
            elevation=610, distance_to_waterbody=0.5,
        )
        assert result_low["cascade_risk_score"] < result["cascade_risk_score"]
    test("CascadeAnalyzer risk levels", test_cascade)

    # --- Exposure Analyzer ---
    def test_exposure():
        from backend.services.infrastructure.exposure_analyzer import ExposureAnalyzer
        analyzer = ExposureAnalyzer()

        result = analyzer.analyze("Kedarnath", origin_probability=0.85)
        assert result["total_bridges_at_risk"] > 0
        assert result["total_road_segments_at_risk"] > 0
        assert len(result["exposed_bridges"]) > 0
    test("ExposureAnalyzer finds at-risk infrastructure", test_exposure)

    # --- LSET Calculator ---
    def test_lset():
        from backend.services.lset.lset_calculator import LSETCalculator
        calc = LSETCalculator()

        result = calc.calculate("Kedarnath", "Sonprayag", origin_probability=0.85)
        assert "lset" in result
        assert "urgency" in result
        assert result["safety_buffer_minutes"] > 0
    test("LSETCalculator single location", test_lset)

    # --- LSET for all ---
    def test_lset_all():
        from backend.services.lset.lset_calculator import LSETCalculator
        calc = LSETCalculator()

        results = calc.calculate_for_all_downstream("Kedarnath", origin_probability=0.85)
        assert len(results) > 3
        # Verify urgency ordering (closest should be most urgent)
        urgencies = [r["urgency"] for r in results]
        assert urgencies[0] in ("EXPIRED", "EVACUATE_NOW"), f"First should be urgent: {urgencies[0]}"
    test("LSETCalculator all downstream with urgency order", test_lset_all)

    # --- Confidence Estimator ---
    def test_confidence():
        from backend.services.prediction.confidence import ConfidenceEstimator
        est = ConfidenceEstimator()

        # High-quality data
        conf = est.estimate(
            model_probability=0.85, data_age_minutes=5,
            feature_completeness=0.95, terrain_data_available=True,
            historical_data_available=True, forecast_available=True,
        )
        assert conf["confidence_level"] == "HIGH"
        assert conf["confidence_score"] > 0.7

        # Low-quality data
        conf_low = est.estimate(
            model_probability=0.5, data_age_minutes=200,
            feature_completeness=0.3, terrain_data_available=False,
            historical_data_available=False, forecast_available=False,
        )
        assert conf_low["confidence_score"] < conf["confidence_score"]
    test("ConfidenceEstimator quality scoring", test_confidence)

    # --- ML Model loading ---
    def test_ml_model_exists():
        model_path = os.path.join("ml", "saved_models", "flood_random_forest.joblib")
        assert os.path.exists(model_path), f"Model not found at {model_path}"
        import joblib
        model = joblib.load(model_path)
        assert hasattr(model, "predict_proba")
    test("ML model file exists and loads", test_ml_model_exists)

    # --- Prediction Service ---
    def test_prediction_service_init():
        from backend.services.prediction.prediction_service import PredictionService
        svc = PredictionService()
        assert svc is not None
        assert svc._model is None  # Lazy loaded
        svc._load_model()
        assert svc._model is not None
    test("PredictionService initializes and loads model", test_prediction_service_init)

    # --- Cross-module data flow ---
    def test_cross_module_flow():
        """Verify propagation -> arrival -> LSET chain produces consistent data."""
        from backend.services.propagation.flood_propagation import FloodPropagationEngine
        from backend.services.arrival_time.arrival_estimator import ArrivalTimeEstimator
        from backend.services.lset.lset_calculator import LSETCalculator

        prop = FloodPropagationEngine()
        arr = ArrivalTimeEstimator()
        lset = LSETCalculator()

        # Propagation
        prop_result = prop.propagate("Kedarnath", 0.85, rainfall_intensity=1.5)
        prop_locs = set()
        for step in prop_result["time_steps"]:
            for loc in step.get("affected_locations", []):
                prop_locs.add(loc["name"])

        # Arrival times
        arrivals = arr.estimate_for_all_downstream("Kedarnath", 0.85, rainfall_intensity=1.5)
        arr_locs = {a["location"] for a in arrivals}

        # LSET
        lsets = lset.calculate_for_all_downstream("Kedarnath", 0.85, rainfall_intensity=1.5)
        lset_locs = {l["location"] for l in lsets}

        # All three should cover the same locations
        assert len(prop_locs) > 0
        assert arr_locs == lset_locs, f"Arrival/LSET mismatch: {arr_locs} vs {lset_locs}"

        # LSET time should be before arrival (LSET = arrival - buffer)
        for l in lsets:
            at = l.get("arrival_time")
            lt = l.get("lset")
            if at and lt:
                # Both are ISO strings, string compare is fine
                assert str(at) >= str(lt), f"LSET after arrival at {l['location']}'"
    test("Cross-module data flow (propagation -> arrival -> LSET)", test_cross_module_flow)


# =========================================================================
# SECTION 2: API Integration Tests (server required)
# =========================================================================
def run_api_tests():
    print("\n" + "=" * 60)
    print("  API INTEGRATION TESTS (server at :8000)")
    print("=" * 60)

    try:
        import httpx
    except ImportError:
        print("  [SKIP] httpx not installed -- skipping API tests")
        return

    base = "http://localhost:8000"

    # Check server is alive
    try:
        r = httpx.get(f"{base}/health", timeout=5)
        if r.status_code != 200:
            print("  [SKIP] Backend not running -- start with: python -m uvicorn backend.main:app --port 8000")
            return
    except Exception:
        print("  [SKIP] Backend not running -- start with: python -m uvicorn backend.main:app --port 8000")
        return

    # --- Health ---
    def test_api_health():
        r = httpx.get(f"{base}/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "healthy"
        assert data["version"] == "0.2.0"
    test("GET /health returns healthy", test_api_health)

    # --- Locations ---
    def test_api_locations():
        r = httpx.get(f"{base}/api/locations")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 9
        names = [l["name"] for l in data["locations"]]
        assert "Kedarnath" in names
        assert "Rudraprayag" in names
    test("GET /api/locations returns pilot locations", test_api_locations)

    # --- Risk prediction ---
    def test_api_risk():
        r = httpx.get(f"{base}/api/risk", params={"lat": 30.735, "lon": 79.067}, timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert "risk_probability" in data
        assert "risk_level" in data
        assert data["risk_level"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
        assert "confidence" in data
        assert "rainfall" in data
        assert "cascade" in data
    test("GET /api/risk returns full risk assessment", test_api_risk)

    # --- Risk map ---
    def test_api_risk_map():
        r = httpx.get(f"{base}/api/risk-map", timeout=60)
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 9
        assert len(data["locations"]) >= 9
        # Each location should have risk data
        for loc in data["locations"]:
            if "error" not in loc:
                assert "risk_probability" in loc
    test("GET /api/risk-map returns all locations", test_api_risk_map)

    # --- Rainfall ---
    def test_api_rainfall():
        r = httpx.get(f"{base}/api/rainfall/current", params={"lat": 30.735, "lon": 79.067}, timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert "rainfall_features" in data
        rf = data["rainfall_features"]
        assert "rain_1h" in rf
        assert "rain_24h" in rf
    test("GET /api/rainfall/current returns features", test_api_rainfall)

    # --- Forecast ---
    def test_api_forecast():
        r = httpx.get(f"{base}/api/weather/forecast", params={"lat": 30.735, "lon": 79.067, "hours": 12}, timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert "current" in data
        assert "forecast_rainfall" in data
    test("GET /api/weather/forecast returns data", test_api_forecast)

    # --- Propagation ---
    def test_api_propagation():
        r = httpx.get(f"{base}/api/propagation", params={"origin": "Kedarnath", "probability": 0.85})
        assert r.status_code == 200
        data = r.json()
        assert data["total_steps"] > 0
        assert data["total_locations_affected"] > 0
    test("GET /api/propagation Kedarnath", test_api_propagation)

    # --- Propagation invalid ---
    def test_api_propagation_invalid():
        r = httpx.get(f"{base}/api/propagation", params={"origin": "InvalidCity", "probability": 0.5})
        assert r.status_code == 404
    test("GET /api/propagation invalid origin -> 404", test_api_propagation_invalid)

    # --- Arrival time ---
    def test_api_arrival():
        r = httpx.get(f"{base}/api/arrival-time", params={"origin": "Kedarnath", "target": "Sonprayag"})
        assert r.status_code == 200
        data = r.json()
        assert data["travel_time_minutes"] > 0
    test("GET /api/arrival-time Kedarnath->Sonprayag", test_api_arrival)

    # --- All arrivals ---
    def test_api_arrivals_all():
        r = httpx.get(f"{base}/api/arrival-time/all", params={"origin": "Kedarnath"})
        assert r.status_code == 200
        data = r.json()
        assert len(data["downstream_arrivals"]) > 3
    test("GET /api/arrival-time/all returns downstream", test_api_arrivals_all)

    # --- Cascade ---
    def test_api_cascade():
        r = httpx.get(f"{base}/api/cascade", params={"location": "Gaurikund", "rain_6h": 80, "rain_24h": 200})
        assert r.status_code == 200
        data = r.json()
        assert data["cascade_risk_level"] in ("HIGH", "CRITICAL")
    test("GET /api/cascade high-rain scenario", test_api_cascade)

    # --- Infrastructure ---
    def test_api_infra():
        r = httpx.get(f"{base}/api/infrastructure/risk", params={"origin": "Kedarnath", "probability": 0.85})
        assert r.status_code == 200
        data = r.json()
        assert data["total_bridges_at_risk"] > 0
    test("GET /api/infrastructure/risk returns bridges", test_api_infra)

    # --- LSET ---
    def test_api_lset():
        r = httpx.get(f"{base}/api/lset", params={"origin": "Kedarnath", "target": "Sonprayag"})
        assert r.status_code == 200
        data = r.json()
        assert "urgency" in data
        assert "lset" in data
    test("GET /api/lset Kedarnath->Sonprayag", test_api_lset)

    # --- LSET All ---
    def test_api_lset_all():
        r = httpx.get(f"{base}/api/lset/all", params={"origin": "Kedarnath"})
        assert r.status_code == 200
        data = r.json()
        results = data["lset_results"]
        assert len(results) > 3
        # First should be most urgent
        assert results[0]["urgency"] in ("EXPIRED", "EVACUATE_NOW")
    test("GET /api/lset/all urgency ordering", test_api_lset_all)


# =========================================================================
# SECTION 3: Scenario Simulation Test
# =========================================================================
def run_scenario_test():
    print("\n" + "=" * 60)
    print("  SCENARIO TEST: Kedarnath Heavy Rainfall Event")
    print("=" * 60)

    from backend.services.propagation.flood_propagation import FloodPropagationEngine
    from backend.services.arrival_time.arrival_estimator import ArrivalTimeEstimator
    from backend.services.cascade.cascade_analyzer import CascadeAnalyzer
    from backend.services.infrastructure.exposure_analyzer import ExposureAnalyzer
    from backend.services.lset.lset_calculator import LSETCalculator
    from backend.services.prediction.confidence import ConfidenceEstimator

    print("\n  Simulating: Heavy rainfall at Kedarnath (p=0.90, intensity=2.5x)")
    print("  " + "-" * 56)

    # 1. Propagation
    prop = FloodPropagationEngine()
    result = prop.propagate("Kedarnath", 0.90, rainfall_intensity=2.5)

    def test_scenario_propagation():
        assert result["total_locations_affected"] >= 8
        assert result["total_steps"] >= 8
    test("Scenario: Propagation reaches 8+ locations", test_scenario_propagation)

    # 2. Arrival times
    arr = ArrivalTimeEstimator()
    arrivals = arr.estimate_for_all_downstream("Kedarnath", 0.90, rainfall_intensity=2.5)

    def test_scenario_arrivals():
        times = {a["location"]: a["travel_time_minutes"] for a in arrivals}
        # Gaurikund should be reached before Sonprayag
        assert times.get("Gaurikund", 999) < times.get("Sonprayag", 999)
        # Rudraprayag should take the longest
        assert times.get("Rudraprayag", 0) > times.get("Sonprayag", 999)
    test("Scenario: Arrival time ordering is physically plausible", test_scenario_arrivals)

    print("\n  Arrival times:")
    for a in arrivals:
        print(f"    {a['location']:<15} +{a['travel_time_minutes']}min  conf={a['confidence']}")

    # 3. Cascade at Gaurikund
    cascade = CascadeAnalyzer()
    casc = cascade.analyze(
        location_name="Gaurikund",
        rain_6h=100, rain_24h=250,
        slope=28, landslide_susceptibility=0.78,
        elevation=1982, distance_to_waterbody=0.1,
        rainfall_intensity=2.5,
    )

    def test_scenario_cascade():
        assert casc["cascade_risk_level"] == "CRITICAL"
        assert "chain" in casc
    test("Scenario: Gaurikund cascade is CRITICAL", test_scenario_cascade)

    # 4. Infrastructure
    infra = ExposureAnalyzer()
    exposure = infra.analyze("Kedarnath", 0.90, rainfall_intensity=2.5)

    def test_scenario_infra():
        assert exposure["total_bridges_at_risk"] >= 5
        critical_bridges = [b for b in exposure["exposed_bridges"] if b["risk_level"] == "CRITICAL"]
        assert len(critical_bridges) >= 2
    test("Scenario: 5+ bridges at risk, 2+ CRITICAL", test_scenario_infra)

    print(f"\n  Infrastructure: {exposure['total_bridges_at_risk']} bridges, {exposure['total_road_segments_at_risk']} roads")

    # 5. LSET
    lset = LSETCalculator()
    lsets = lset.calculate_for_all_downstream("Kedarnath", 0.90, rainfall_intensity=2.5)

    def test_scenario_lset():
        urgencies = {l["location"]: l["urgency"] for l in lsets}
        # Gaurikund should be EXPIRED or EVACUATE_NOW
        assert urgencies.get("Gaurikund") in ("EXPIRED", "EVACUATE_NOW")
    test("Scenario: Gaurikund LSET is EXPIRED/EVACUATE_NOW", test_scenario_lset)

    print("\n  Evacuation timeline:")
    for l in lsets:
        print(f"    {l['location']:<15} urgency={l['urgency']:<22} LSET={l['time_until_lset_minutes']}min  buffer={l['safety_buffer_minutes']}min")

    # 6. Confidence
    conf = ConfidenceEstimator()
    c = conf.estimate(
        model_probability=0.90, data_age_minutes=3,
        feature_completeness=0.95, terrain_data_available=True,
        historical_data_available=True, forecast_available=True,
    )

    def test_scenario_confidence():
        assert c["confidence_level"] == "HIGH"
        assert c["confidence_score"] > 0.8
    test("Scenario: Confidence is HIGH with good data", test_scenario_confidence)


# =========================================================================
# MAIN
# =========================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("  NeerNetra -- Phase 7 Integration Test Suite")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    t0 = time.time()

    run_unit_tests()
    run_scenario_test()
    run_api_tests()

    elapsed = time.time() - t0

    print("\n" + "=" * 60)
    print(f"  RESULTS: {RESULTS['passed']} passed, {RESULTS['failed']} failed")
    print(f"  Time: {elapsed:.1f}s")
    print("=" * 60)

    if RESULTS["errors"]:
        print("\n  Failures:")
        for err in RESULTS["errors"]:
            print(f"    - {err}")

    print()
    sys.exit(0 if RESULTS["failed"] == 0 else 1)
