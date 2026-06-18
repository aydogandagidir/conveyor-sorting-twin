"""Phase 0 verification — proves Engineering Gate 1 end to end.

Loop proven (Modbus TCP proof path):
  virtual sensor event -> tag registry -> protocol gateway (Modbus TCP) ->
  soft-PLC control logic -> actuator output tag -> simulation reads output ->
  telemetry event logged.

A second pass proves the in-process local control fallback (no sockets).

Run:  python tests/verify_phase0.py
Exit: 0 = all checks pass, 1 = a check failed.
"""
from __future__ import annotations

import os
import sys
import tempfile
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _sub in ("protocol-gateway", "plc", "telemetry", "simulation"):
    sys.path.insert(0, os.path.join(_ROOT, _sub))

from tag_registry import TagRegistry          # noqa: E402
from modbus_tcp import ModbusTCPClient, LocalStoreClient  # noqa: E402
from gateway import TagGateway                 # noqa: E402
from soft_plc import SoftPlc                   # noqa: E402
from telemetry_logger import TelemetryLogger   # noqa: E402
from cell_sim import ConveyorCellSimulator     # noqa: E402

REGISTRY_PATH = os.path.join(_ROOT, "protocol-gateway", "config", "tags.conveyor_sorting_cell.json")
EXPORT_DIR = os.path.join(_ROOT, "telemetry", "exports")

_checks = []


class CheckFailure(Exception):
    pass


def check(label: str, condition, detail: str = ""):
    ok = bool(condition)
    _checks.append((label, ok))
    suffix = f"  ({detail})" if detail else ""
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}{suffix}")
    if not ok:
        raise CheckFailure(label + (f": {detail}" if detail else ""))


def wait_until(predicate, timeout: float = 3.0, interval: float = 0.01) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        if predicate():
            return True
        time.sleep(interval)
    return False


def run_modbus_proof():
    print("\n[1/4] Tag registry")
    registry = TagRegistry.from_file(REGISTRY_PATH)
    check("registry loads and validates", len(registry) == 12, f"{len(registry)} tags")
    check("sensor.preDivert -> master-writable coil",
          registry.get("sensor.preDivert").table == "coil")
    check("motor.conveyor -> master-readable discrete_input",
          registry.get("motor.conveyor").table == "discrete_input")

    print("\n[2/4] Soft-PLC (Modbus TCP slave) + gateway (master)")
    plc = SoftPlc(registry, scan_interval=0.01)
    port = plc.serve(host="127.0.0.1", port=0)  # 0 -> OS-assigned free port
    plc.start()
    gw = TagGateway(registry, ModbusTCPClient("127.0.0.1", port)).connect()
    check("gateway connected over real Modbus TCP", True, f"127.0.0.1:{port}")
    gw.initialize_inputs()

    db_path = os.path.join(tempfile.mkdtemp(prefix="oltwin_"), "telemetry.db")
    tel = TelemetryLogger(db_path, scenario="phase0-verify")
    sim = ConveyorCellSimulator(gw, tel)

    print("\n[3/4] Gate-1 control loop (sensor -> gateway -> PLC -> actuator -> telemetry)")
    # E-stop engaged -> motor must stop (safety wins).
    sim.set_estop(True)
    check("E-stop engaged stops the motor",
          wait_until(lambda: gw.read_tag("motor.conveyor") is False))
    tel.log_tag_change("motor.conveyor", True, False, "estop engaged")

    # E-stop released -> conveyor runs.
    sim.set_estop(False)
    check("motor runs after E-stop release",
          wait_until(lambda: gw.read_tag("motor.conveyor") is True))
    tel.log_tag_change("motor.conveyor", False, True, "estop released")
    check("running indicator energised", gw.read_tag("indicator.running") is True)

    # Route one parcel to each destination.
    for index, dest in enumerate([1, 2, 3], start=1):
        sim.present_parcel(dest)
        counted = wait_until(lambda: gw.read_tag("throughput.count") == index)
        arm_a = gw.read_tag("diverter.armA")
        arm_b = gw.read_tag("diverter.armB")
        check(f"parcel {index} counted (dest={dest})", counted,
              f"count={gw.read_tag('throughput.count')}")
        if dest == 1:
            check("dest=1 routes to arm A only", arm_a is True and arm_b is False,
                  f"armA={arm_a} armB={arm_b}")
        elif dest == 2:
            check("dest=2 routes to arm B only", arm_b is True and arm_a is False,
                  f"armA={arm_a} armB={arm_b}")
        else:
            check("dest=3 goes straight (no arm)", arm_a is False and arm_b is False,
                  f"armA={arm_a} armB={arm_b}")
        tel.log_event("sorted", tag="diverter", value=dest, detail=f"armA={arm_a},armB={arm_b}")
        sim.clear_parcel()
        wait_until(lambda: gw.read_tag("diverter.armA") is False
                   and gw.read_tag("diverter.armB") is False)

    check("throughput.count reached 3", gw.read_tag("throughput.count") == 3,
          f"count={gw.read_tag('throughput.count')}")

    print("\n[4/4] Telemetry export (SQLite -> CSV/JSON)")
    check("telemetry events recorded", tel.count() > 0, f"{tel.count()} events")
    csv_path = tel.export_csv(os.path.join(EXPORT_DIR, "phase0_verify.csv"))
    json_path = tel.export_json(os.path.join(EXPORT_DIR, "phase0_verify.json"))
    check("CSV export written", os.path.getsize(csv_path) > 0,
          os.path.relpath(csv_path, _ROOT))
    check("JSON export written", os.path.getsize(json_path) > 0,
          os.path.relpath(json_path, _ROOT))
    import json as _json
    with open(json_path, encoding="utf-8") as f:
        payload = _json.load(f)
    check("JSON export parses with events",
          payload.get("count", 0) == len(payload.get("events", [])) and payload["count"] > 0,
          f"{payload.get('count')} events")

    tel.close()
    gw.close()
    plc.stop()


def run_local_fallback():
    print("\n[local fallback] in-process control (no sockets)")
    registry = TagRegistry.from_file(REGISTRY_PATH)
    plc = SoftPlc(registry, scan_interval=0.01)
    gw = TagGateway(registry, LocalStoreClient(plc.store)).connect()  # share the store
    plc.start()
    gw.initialize_inputs()
    gw.write_tag("estop", False)
    gw.write_tag("barcode.destination", 2)
    gw.write_tag("sensor.preDivert", True)
    ok = wait_until(lambda: gw.read_tag("diverter.armB") is True
                    and gw.read_tag("motor.conveyor") is True)
    check("local fallback routes dest=2 to arm B without TCP", ok)
    plc.stop()


def main() -> int:
    print("=" * 66)
    print("OpenLogiTwin - Phase 0 Verification (Engineering Gate 1)")
    print("=" * 66)
    try:
        run_modbus_proof()
        run_local_fallback()
    except CheckFailure as e:
        print(f"\nRESULT: FAIL - {e}")
        return 1
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        print(f"\nRESULT: FAIL - unexpected error: {e}")
        return 1
    passed = sum(1 for _, ok in _checks if ok)
    print("\n" + "=" * 66)
    print(f"RESULT: PASS - {passed}/{len(_checks)} checks passed")
    print("=" * 66)
    return 0


if __name__ == "__main__":
    sys.exit(main())
