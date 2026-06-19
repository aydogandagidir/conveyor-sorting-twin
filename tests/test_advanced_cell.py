"""Advanced (FIFO-ring) sorting cell — promoted from the Phase 1.5f prototype (ADR-0005).

Proves the committed advanced cell routes a dense parcel stream correctly through the full
stack (registry + cell-aware runner + scenario manager), and that the single-register MVP
cell mis-routes the identical stream — i.e. the FIFO ring fixes a real defect.

Dual-mode: `python tests/test_advanced_cell.py` (exit 0/1) or pytest.
"""
import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
for _sub in ("protocol-gateway", "plc", "telemetry", "simulation"):
    sys.path.insert(0, os.path.join(_ROOT, _sub))

import scenario_manager          # noqa: E402
import control_logic_mvp         # noqa: E402
from scenario_runner import ScenarioRunner  # noqa: E402

DENSE = os.path.join(_ROOT, "scenarios", "dense_sort_advanced.json")
MVP_REGISTRY = os.path.join(_ROOT, "protocol-gateway", "config", "tags.sorting_cell_mvp.json")


def test_advanced_cell_routes_dense_stream_correctly():
    result, _expect, mismatches = scenario_manager.run_and_check(DENSE, use_modbus=False)
    assert not mismatches, mismatches
    assert (result["sorted_a"], result["sorted_b"]) == (4, 4)
    assert len(result["scene_chute_a"]) + len(result["scene_chute_b"]) == 8
    assert result["jam_triggered"] is False


def test_same_stream_misroutes_on_mvp_single_register():
    scenario = json.load(open(DENSE, encoding="utf-8"))
    runner = ScenarioRunner(MVP_REGISTRY, use_modbus=False,
                            control=control_logic_mvp, dest_strategy="single")
    result = runner.run(scenario)
    runner.close()
    assert result["sorted_a"] + result["sorted_b"] == 8          # every parcel is counted...
    assert (result["sorted_a"], result["sorted_b"]) != (4, 4)    # ...but mis-split: the ring is needed


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
    print(f"\nadvanced cell tests: {passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
