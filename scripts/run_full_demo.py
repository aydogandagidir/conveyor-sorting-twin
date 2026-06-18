"""End-to-end demo: run the scenario suite, aggregate metrics, emit a report.

One command runs all shipped scenarios deterministically, checks each `expect` block,
aggregates throughput/sort/fault metrics into telemetry/exports/demo_results.json, and
renders a self-contained HTML + Markdown report.

Usage:
  python scripts/run_full_demo.py [--export-dir=DIR] [--modbus] [--no-report]
"""
import json
import os
import sys
from datetime import datetime, timezone

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
for _sub in ("protocol-gateway", "plc", "telemetry", "simulation"):
    sys.path.insert(0, os.path.join(_ROOT, _sub))

import scenario_manager           # noqa: E402
import generate_demo_report       # noqa: E402

EXPORTS = os.path.join(_ROOT, "telemetry", "exports")
DEMO_SCENARIOS = [
    "barcode_sorting_basic",
    "jam_recovery_basic",
    "estop_during_run",
    "stop_button_basic",
    "rapid_jam_reset",
]


def run_demo(export_dir=EXPORTS, use_modbus=False, timestamp=None):
    rows = []
    for name in DEMO_SCENARIOS:
        path = scenario_manager.resolve(name)
        scenario = json.load(open(path, encoding="utf-8"))
        dt = float(scenario.get("dt", 0.05))
        result, _expect, mismatches = scenario_manager.run_and_check(
            path, export_dir=export_dir, use_modbus=use_modbus)
        rows.append({
            "name": result["name"],
            "sorted_a": result["sorted_a"],
            "sorted_b": result["sorted_b"],
            "parcels": result["sorted_a"] + result["sorted_b"],
            "jam_triggered": result["jam_triggered"],
            "jam_cleared": result["jam_cleared"],
            "sim_seconds": round(result["ticks"] * dt, 2),
            "expect_pass": not mismatches,
            "mismatches": mismatches,
        })

    sim_seconds = round(sum(r["sim_seconds"] for r in rows), 2)
    parcels = sum(r["parcels"] for r in rows)
    totals = {
        "scenarios": len(rows),
        "expect_passed": sum(1 for r in rows if r["expect_pass"]),
        "parcels_sorted": parcels,
        "sorted_a": sum(r["sorted_a"] for r in rows),
        "sorted_b": sum(r["sorted_b"] for r in rows),
        "jams": sum(1 for r in rows if r["jam_triggered"]),
        "sim_seconds": sim_seconds,
        "parcels_per_min": round(parcels / (sim_seconds / 60), 1) if sim_seconds else 0.0,
    }
    return {
        "generated_at": timestamp or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "transport": "local" if not use_modbus else "modbus-tcp",
        "scenarios": rows,
        "totals": totals,
    }


def main(argv):
    export_dir = EXPORTS
    for a in argv:
        if a.startswith("--export-dir="):
            export_dir = a.split("=", 1)[1]
    # Demo defaults to in-process (deterministic, fast); pass --modbus for real TCP.
    use_modbus = "--modbus" in argv
    data = run_demo(export_dir=export_dir, use_modbus=use_modbus)

    os.makedirs(export_dir, exist_ok=True)
    results_path = os.path.join(export_dir, "demo_results.json")
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    t = data["totals"]
    print(f"Demo complete: {t['parcels_sorted']} parcels, {t['parcels_per_min']} parcels/min, "
          f"sort_a={t['sorted_a']}, sort_b={t['sorted_b']}, {t['jams']} jam(s), "
          f"expect {t['expect_passed']}/{t['scenarios']}")
    print(f"Results: {os.path.relpath(results_path, _ROOT)}")

    if "--no-report" not in argv:
        html_path, md_path = generate_demo_report.generate(results_path, export_dir)
        print(f"Report : {os.path.relpath(html_path, _ROOT)} , {os.path.relpath(md_path, _ROOT)}")

    return 0 if t["expect_passed"] == t["scenarios"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
