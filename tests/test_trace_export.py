"""V0 — deterministic per-tick trace export for the web HMI.

Verifies a scenario trace is structurally complete, reproducible (same scenario → identical
frames), and physically consistent (parcels advance under the motor; the final frame's counters
match the run result). The trace is what the browser HMI replays. Stdlib only. Dual-mode.
"""
import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, os.path.join(_ROOT, "simulation"))

import scenario_manager as sm        # noqa: E402
from scenario_runner import ScenarioRunner  # noqa: E402


def _trace(name):
    with open(sm.resolve(name), encoding="utf-8") as f:
        scenario = json.load(f)
    prof = sm._profile(scenario)
    runner = ScenarioRunner(prof["registry"], use_modbus=False,
                            control=prof["control"], dest_strategy=prof["dest_strategy"])
    try:
        return runner.run(scenario, record_trace=True)
    finally:
        runner.close()


def test_trace_structure_and_final_counts():
    res = _trace("barcode_sorting_basic")
    tr = res["trace"]
    assert tr["layout"]["pe1"] == 20.0 and tr["layout"]["end"] == 120.0
    assert tr["frames"], "no frames recorded"
    f0 = tr["frames"][0]
    assert {"t", "motor", "diverter", "jam", "a", "b", "pe1", "pe2", "parcels"} <= set(f0)
    # the trace's final counters must equal the run result (no drift)
    assert tr["frames"][-1]["a"] == res["sorted_a"]
    assert tr["frames"][-1]["b"] == res["sorted_b"]


def test_trace_is_deterministic():
    a = _trace("barcode_routing")["trace"]["frames"]
    b = _trace("barcode_routing")["trace"]["frames"]
    assert a == b, "trace not reproducible"


def test_parcels_advance_under_motor():
    tr = _trace("barcode_sorting_basic")["trace"]
    xs = [p["x"] for fr in tr["frames"] for p in fr["parcels"] if p["id"] == "P1"]
    assert len(xs) >= 2 and xs[-1] > xs[0], "parcel P1 did not advance"


def test_export_writes_files_and_manifest():
    """The exporter's file-writing path is the seam the browser HMI fetches: per-scenario
    JSON (with the keys hmi.js reads) + an index.json manifest. Exercise it end to end."""
    import shutil
    import tempfile
    import export_trace
    out = tempfile.mkdtemp()
    orig = export_trace.OUT
    export_trace.OUT = out
    try:
        assert export_trace.main(["barcode_sorting_basic"]) == 0
        scenario_json = os.path.join(out, "barcode_sorting_basic.json")
        assert os.path.exists(scenario_json), "per-scenario trace file not written"
        with open(scenario_json, encoding="utf-8") as f:
            tr = json.load(f)
        assert {"frames", "dt", "layout"} <= set(tr), "trace JSON missing keys the HMI reads"
        with open(os.path.join(out, "index.json"), encoding="utf-8") as f:
            manifest = json.load(f)
        assert "barcode_sorting_basic" in manifest["traces"], "manifest omits the scenario"
    finally:
        export_trace.OUT = orig
        shutil.rmtree(out, ignore_errors=True)


def _all_tests():
    return [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]


def main():
    passed = 0
    for t in _all_tests():
        t(); print(f"  [PASS] {t.__name__}"); passed += 1
    print(f"trace export tests: {passed} passed, 0 failed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
