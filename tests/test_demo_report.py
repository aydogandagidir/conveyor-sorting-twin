"""Tests for the Phase 3c demo runner + report generator.

Runs the full demo (all scenarios) and renders the report, asserting the aggregate
metrics and that a self-contained HTML + Markdown report are produced.

Dual-mode: `python tests/test_demo_report.py` (exit 0/1) or pytest.
"""
import json
import os
import sys
import tempfile

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
for _sub in ("protocol-gateway", "plc", "telemetry", "simulation"):
    sys.path.insert(0, os.path.join(_ROOT, _sub))

import run_full_demo          # noqa: E402
import generate_demo_report   # noqa: E402


def test_demo_runs_and_all_scenarios_pass():
    data = run_full_demo.run_demo(export_dir=tempfile.mkdtemp(prefix="oltwin_demo_"),
                                  use_modbus=False, timestamp="TEST")
    t = data["totals"]
    assert t["scenarios"] == len(run_full_demo.DEMO_SCENARIOS)
    assert t["expect_passed"] == t["scenarios"], data["scenarios"]
    assert t["parcels_sorted"] == t["sorted_a"] + t["sorted_b"]
    assert t["parcels_sorted"] > 0
    assert t["jams"] >= 1  # jam_recovery + rapid_jam_reset


def test_report_html_and_md_are_written_and_self_contained():
    out = tempfile.mkdtemp(prefix="oltwin_report_")
    data = run_full_demo.run_demo(export_dir=out, use_modbus=False, timestamp="TEST")
    results = os.path.join(out, "demo_results.json")
    with open(results, "w", encoding="utf-8") as f:
        json.dump(data, f)
    html_path, md_path = generate_demo_report.generate(results, out)

    html = open(html_path, encoding="utf-8").read()
    assert os.path.getsize(html_path) > 0 and os.path.getsize(md_path) > 0
    assert "<!doctype html>" in html.lower()
    assert "http://" not in html and "https://" not in html and "cdn" not in html.lower()  # self-contained
    for s in data["scenarios"]:
        assert s["name"] in html
    assert "parcels sorted" in html.lower()


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
    print(f"\ndemo report tests: {passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
