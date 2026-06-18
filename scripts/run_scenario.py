"""Run a Phase 1 sorting-cell scenario deterministically and export telemetry.

Usage:
  python scripts/run_scenario.py                                  # runs barcode_sorting_basic
  python scripts/run_scenario.py scenarios/jam_recovery_basic.json
  python scripts/run_scenario.py <scenario.json> --local          # in-process (no TCP)

Writes telemetry to telemetry/exports/<scenario>.{json,csv} and prints a summary.
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _sub in ("protocol-gateway", "plc", "telemetry", "simulation"):
    sys.path.insert(0, os.path.join(_ROOT, _sub))

from scenario_runner import ScenarioRunner  # noqa: E402

REGISTRY = os.path.join(_ROOT, "protocol-gateway", "config", "tags.sorting_cell_mvp.json")
EXPORTS = os.path.join(_ROOT, "telemetry", "exports")


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    use_modbus = "--local" not in argv
    export_dir = EXPORTS
    for a in argv:
        if a.startswith("--export-dir="):
            export_dir = a.split("=", 1)[1]
    scenario_path = args[0] if args else os.path.join(_ROOT, "scenarios", "barcode_sorting_basic.json")
    if not os.path.isabs(scenario_path):
        scenario_path = os.path.join(_ROOT, scenario_path)
    name = os.path.splitext(os.path.basename(scenario_path))[0]

    runner = ScenarioRunner(REGISTRY, use_modbus=use_modbus)
    res = runner.run_file(scenario_path)
    json_path = runner.tel.export_json(os.path.join(export_dir, f"{name}.json"))
    csv_path = runner.tel.export_csv(os.path.join(export_dir, f"{name}.csv"))
    runner.close()

    print(f"Scenario     : {res['name']}")
    print(f"Transport    : {res['transport']}")
    print(f"Ticks        : {res['ticks']}  (motor-on {res['motor_on_ticks']})")
    print(f"Parcels      : {[d[1] for d in res['destinations']]}")
    print(f"Sorted A / B : {res['sorted_a']} / {res['sorted_b']}")
    print(f"Scene chutes : A={res['scene_chute_a']}  B={res['scene_chute_b']}")
    print(f"Jam          : triggered={res['jam_triggered']} cleared={res['jam_cleared']}")
    print(f"Telemetry    : {res['telemetry_events']} events")
    print(f"Exported     : {os.path.relpath(json_path, _ROOT)} , {os.path.relpath(csv_path, _ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
