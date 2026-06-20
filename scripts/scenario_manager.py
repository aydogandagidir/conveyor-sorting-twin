"""Scenario manager (CLI) for the OpenLogiTwin sorting cell — Phase 2.

Lists, validates and runs deterministic scenarios (including fault-injection ones)
against the soft-PLC over Modbus, checks each scenario's `expect` block, and exports
telemetry. The scenarios carry the operator controls (start / stop / reset / E-stop)
and faults (inject_jam), so this CLI is also the fault-injection front end until the
FUXA panel lands.

Usage:
  python scripts/scenario_manager.py list
  python scripts/scenario_manager.py validate scenarios/rapid_jam_reset.json
  python scripts/scenario_manager.py run rapid_jam_reset [--export-dir=DIR] [--local] [--mqtt-host=HOST[:PORT]]
  python scripts/scenario_manager.py run-all [--export-dir=DIR] [--local] [--mqtt-host=HOST[:PORT]]

The --mqtt-host flag streams each telemetry event to an MQTT broker (requires paho-mqtt).
"""
import glob
import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _sub in ("protocol-gateway", "plc", "telemetry", "simulation"):
    sys.path.insert(0, os.path.join(_ROOT, _sub))

from scenario_runner import ScenarioRunner, validate_scenario  # noqa: E402
import control_logic_mvp       # noqa: E402
import control_logic_advanced  # noqa: E402

_CONFIG = os.path.join(_ROOT, "protocol-gateway", "config")
REGISTRY = os.path.join(_CONFIG, "tags.sorting_cell_mvp.json")   # default cell
SCEN_DIR = os.path.join(_ROOT, "scenarios")

# A scenario's "cell" field selects the runner profile.
CELL_PROFILES = {
    "sorting_cell_mvp": {
        "registry": os.path.join(_CONFIG, "tags.sorting_cell_mvp.json"),
        "control": control_logic_mvp, "dest_strategy": "single",
    },
    "sorting_cell_advanced": {
        "registry": os.path.join(_CONFIG, "tags.sorting_cell_advanced.json"),
        "control": control_logic_advanced, "dest_strategy": "fifo_ring",
    },
}


def _profile(scenario):
    return CELL_PROFILES.get(scenario.get("cell", "sorting_cell_mvp"),
                             CELL_PROFILES["sorting_cell_mvp"])


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


def make_mqtt_publisher(argv):
    """Build a connected MqttTelemetryPublisher from --mqtt-host=HOST[:PORT], or None."""
    spec = None
    for a in argv:
        if a.startswith("--mqtt-host="):
            spec = a.split("=", 1)[1]
    if not spec:
        return None
    host, _, port = spec.partition(":")
    from mqtt_publisher import MqttTelemetryPublisher
    return MqttTelemetryPublisher(host=host, port=int(port) if port else 1883).connect()


def run_and_check(path, export_dir=None, use_modbus=True, telemetry_sink=None):
    """Run a scenario on its cell profile; return (result, expect, mismatches)."""
    with open(path, encoding="utf-8") as f:
        scenario = json.load(f)
    prof = _profile(scenario)
    runner = ScenarioRunner(prof["registry"], use_modbus=use_modbus,
                            control=prof["control"], dest_strategy=prof["dest_strategy"],
                            telemetry_sink=telemetry_sink)
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
    pub = make_mqtt_publisher(argv)
    try:
        result, expect, mm = run_and_check(path, export_dir, use_modbus="--local" not in argv,
                                           telemetry_sink=pub.as_sink() if pub else None)
    finally:
        if pub:
            pub.close()
    _print_result(result["name"] or os.path.basename(path), result, expect, mm)
    return 1 if mm else 0


def cmd_run_all(argv):
    export_dir = _export_dir(argv)
    use_modbus = "--local" not in argv
    pub = make_mqtt_publisher(argv)
    sink = pub.as_sink() if pub else None
    failures = 0
    print(f"Running {len(scenario_files())} scenarios...")
    try:
        for path in scenario_files():
            result, expect, mm = run_and_check(path, export_dir, use_modbus=use_modbus,
                                               telemetry_sink=sink)
            _print_result(result["name"] or os.path.basename(path), result, expect, mm)
            if mm:
                failures += 1
    finally:
        if pub:
            pub.close()
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
