"""Scenario manager (CLI) for the OpenLogiTwin sorting cell — Phase 2.

Lists, validates and runs deterministic scenarios (including fault-injection ones)
against the soft-PLC over Modbus, checks each scenario's `expect` block, and exports
telemetry. The scenarios carry the operator controls (start / stop / reset / E-stop)
and faults (inject_jam), so this CLI is also the fault-injection front end until the
FUXA panel lands.

Usage:
  python scripts/scenario_manager.py list
  python scripts/scenario_manager.py validate scenarios/rapid_jam_reset.json
  python scripts/scenario_manager.py run rapid_jam_reset [--export-dir=DIR] [--local]
  python scripts/scenario_manager.py run-all [--export-dir=DIR] [--local]
"""
import glob
import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _sub in ("protocol-gateway", "plc", "telemetry", "simulation"):
    sys.path.insert(0, os.path.join(_ROOT, _sub))

from scenario_runner import ScenarioRunner, validate_scenario  # noqa: E402

REGISTRY = os.path.join(_ROOT, "protocol-gateway", "config", "tags.sorting_cell_mvp.json")
SCEN_DIR = os.path.join(_ROOT, "scenarios")


def scenario_files():
    return sorted(
        f for f in glob.glob(os.path.join(SCEN_DIR, "*.json"))
        if os.path.basename(f) != "schema.json"
    )


def resolve(name):
    if os.path.isabs(name) and os.path.exists(name):
        return name
    for cand in (name, name + ".json",
                 os.path.join(SCEN_DIR, name), os.path.join(SCEN_DIR, name + ".json")):
        if os.path.exists(cand):
            return cand
    raise FileNotFoundError(f"scenario not found: {name}")


def run_and_check(path, export_dir=None, use_modbus=True):
    """Run a scenario; return (result, expect, mismatches)."""
    with open(path, encoding="utf-8") as f:
        scenario = json.load(f)
    runner = ScenarioRunner(REGISTRY, use_modbus=use_modbus)
    result = runner.run(scenario)
    if export_dir:
        name = os.path.splitext(os.path.basename(path))[0]
        runner.tel.export_json(os.path.join(export_dir, f"{name}.json"))
        runner.tel.export_csv(os.path.join(export_dir, f"{name}.csv"))
    runner.close()
    expect = scenario.get("expect", {})
    mismatches = {k: {"expected": v, "actual": result.get(k)}
                  for k, v in expect.items() if result.get(k) != v}
    return result, expect, mismatches


def _export_dir(argv):
    for a in argv:
        if a.startswith("--export-dir="):
            return a.split("=", 1)[1]
    return None


def cmd_list(_argv):
    for path in scenario_files():
        d = json.load(open(path, encoding="utf-8"))
        print(f"  {d.get('name', os.path.basename(path)):22}  {d.get('description', '')[:74]}")
    return 0


def cmd_validate(argv):
    path = resolve(argv[0])
    try:
        validate_scenario(json.load(open(path, encoding="utf-8")))
        print(f"OK   {os.path.basename(path)} is valid")
        return 0
    except ValueError as e:
        print(f"FAIL {os.path.basename(path)}\n{e}")
        return 1


def _print_result(name, result, expect, mismatches):
    verdict = "PASS" if not mismatches else "FAIL"
    extra = f"  expect:{verdict}" if expect else ""
    print(f"  {name:22}  A/B={result['sorted_a']}/{result['sorted_b']}  "
          f"jam={result['jam_triggered']}/{result['jam_cleared']}  "
          f"motor={result['motor_on_ticks']}/{result['ticks']}{extra}")
    if mismatches:
        print(f"       mismatches: {mismatches}")


def cmd_run(argv):
    export_dir = _export_dir(argv)
    name = [a for a in argv if not a.startswith("--")][0]
    path = resolve(name)
    result, expect, mm = run_and_check(path, export_dir, use_modbus="--local" not in argv)
    _print_result(result["name"] or os.path.basename(path), result, expect, mm)
    return 1 if mm else 0


def cmd_run_all(argv):
    export_dir = _export_dir(argv)
    use_modbus = "--local" not in argv
    failures = 0
    print(f"Running {len(scenario_files())} scenarios...")
    for path in scenario_files():
        result, expect, mm = run_and_check(path, export_dir, use_modbus=use_modbus)
        _print_result(result["name"] or os.path.basename(path), result, expect, mm)
        if mm:
            failures += 1
    print("=" * 60)
    print("ALL EXPECTATIONS MET" if not failures else f"{failures} scenario(s) FAILED expectations")
    return 1 if failures else 0


_COMMANDS = {"list": cmd_list, "validate": cmd_validate, "run": cmd_run, "run-all": cmd_run_all}


def main(argv):
    cmd = argv[0] if argv else "run-all"
    if cmd not in _COMMANDS:
        print(__doc__)
        return 2
    return _COMMANDS[cmd](argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
