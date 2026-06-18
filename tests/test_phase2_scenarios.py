"""Phase 2 scenario suite — every scenario must meet its `expect` block.

Drives all scenarios/*.json through the scenario manager and checks the declared
expectations (sorting counts, jam trigger/clear). Covers the fault-injection and
operator-control scenarios (E-stop, Stop button, jam/reset).

Dual-mode: `python tests/test_phase2_scenarios.py` (exit 0/1) or pytest.
"""
import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _sub in ("protocol-gateway", "plc", "telemetry", "simulation", "scripts"):
    sys.path.insert(0, os.path.join(_ROOT, _sub))

from scenario_manager import scenario_files, run_and_check  # noqa: E402

_NEW_FAULT_SCENARIOS = ("estop_during_run", "stop_button_basic", "rapid_jam_reset")


def test_all_scenarios_meet_expectations():
    files = scenario_files()
    assert files, "no scenarios found"
    failures = {}
    for path in files:
        _result, _expect, mismatches = run_and_check(path, use_modbus=False)
        if mismatches:
            failures[os.path.basename(path)] = mismatches
    assert not failures, f"scenario expectations failed: {failures}"


def test_fault_and_control_scenarios_present_with_expectations():
    names = {os.path.splitext(os.path.basename(p))[0]: p for p in scenario_files()}
    for name in _NEW_FAULT_SCENARIOS:
        assert name in names, f"missing scenario: {name}"
        scenario = json.load(open(names[name], encoding="utf-8"))
        assert scenario.get("expect"), f"{name} has no expect block"


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
    print(f"\nPhase 2 scenario tests: {passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
