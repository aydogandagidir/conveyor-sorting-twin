"""Tests for scenario validation (simulation/scenario_runner.validate_scenario).

Confirms the shipped scenarios are valid and that malformed scenarios fail fast.
Dual-mode: `python tests/test_scenario_schema.py` (exit 0/1) or pytest.
"""
import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _sub in ("protocol-gateway", "plc", "telemetry", "simulation"):
    sys.path.insert(0, os.path.join(_ROOT, _sub))

from scenario_runner import validate_scenario  # noqa: E402

SCEN_DIR = os.path.join(_ROOT, "scenarios")


def test_shipped_scenarios_are_valid():
    for fname in ("barcode_sorting_basic.json", "jam_recovery_basic.json"):
        with open(os.path.join(SCEN_DIR, fname), encoding="utf-8") as f:
            assert validate_scenario(json.load(f)) is True, fname


def _expect_invalid(scenario, why):
    try:
        validate_scenario(scenario)
    except ValueError:
        return
    raise AssertionError(f"expected ValueError for {why}")


def test_missing_duration_rejected():
    _expect_invalid({"events": []}, "missing duration")


def test_missing_events_rejected():
    _expect_invalid({"duration": 5.0}, "missing events")


def test_unknown_action_rejected():
    _expect_invalid({"duration": 5.0, "events": [{"t": 0.0, "action": "inject_jam_at"}]}, "unknown action")


def test_press_without_input_rejected():
    _expect_invalid({"duration": 5.0, "events": [{"t": 0.0, "action": "press"}]}, "press without input")


def test_spawn_without_destination_rejected():
    _expect_invalid({"duration": 5.0, "events": [{"t": 0.0, "action": "spawn_parcel"}]}, "spawn without destination")


def test_event_missing_time_rejected():
    _expect_invalid({"duration": 5.0, "events": [{"action": "clear_jam"}]}, "event without t")


def _all_tests():
    return [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]


def main():
    passed = failed = 0
    for t in _all_tests():
        try:
            t()
            print(f"  [PASS] {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  [FAIL] {t.__name__}: {e}")
            failed += 1
    print(f"\nscenario schema tests: {passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
