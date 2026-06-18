"""Human-readable end-to-end demo of the Phase 0 conveyor sorting cell.

Starts the soft-PLC (Modbus TCP slave) in-process, connects the gateway as a
master, runs a stream of parcels through the cell, prints the routing decisions,
and exports telemetry to telemetry/exports/demo.json.

Run: python scripts/run_demo.py
"""
import os
import sys
import tempfile
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _sub in ("protocol-gateway", "plc", "telemetry", "simulation"):
    sys.path.insert(0, os.path.join(_ROOT, _sub))

from tag_registry import TagRegistry         # noqa: E402
from modbus_tcp import ModbusTCPClient        # noqa: E402
from gateway import TagGateway                # noqa: E402
from soft_plc import SoftPlc                  # noqa: E402
from telemetry_logger import TelemetryLogger  # noqa: E402
from cell_sim import ConveyorCellSimulator    # noqa: E402

REGISTRY = os.path.join(_ROOT, "protocol-gateway", "config", "tags.conveyor_sorting_cell.json")
CHUTE = {1: "chute 1", 2: "chute 2", 3: "chute 3 (straight)"}


def wait_until(predicate, timeout=3.0, interval=0.01):
    end = time.time() + timeout
    while time.time() < end:
        if predicate():
            return True
        time.sleep(interval)
    return False


def main():
    registry = TagRegistry.from_file(REGISTRY)
    plc = SoftPlc(registry, scan_interval=0.01)
    port = plc.serve("127.0.0.1", 0)
    plc.start()
    gw = TagGateway(registry, ModbusTCPClient("127.0.0.1", port)).connect()
    db = os.path.join(tempfile.mkdtemp(prefix="oltwin_demo_"), "telemetry.db")
    tel = TelemetryLogger(db, scenario="phase0-demo")
    sim = ConveyorCellSimulator(gw, tel)

    print(f"OpenLogiTwin conveyor sorting cell demo  (Modbus TCP @ 127.0.0.1:{port})")
    print("-" * 60)
    gw.initialize_inputs()
    gw.write_tag("estop", False)
    wait_until(lambda: gw.read_tag("motor.conveyor") is True)
    print(f"Conveyor motor running : {gw.read_tag('motor.conveyor')}")
    print(f"Running indicator      : {gw.read_tag('indicator.running')}")
    print()

    count = 0
    for dest in (1, 2, 3, 1, 2):
        count += 1
        sim.present_parcel(dest)
        wait_until(lambda: gw.read_tag("throughput.count") == count)
        arm_a = gw.read_tag("diverter.armA")
        arm_b = gw.read_tag("diverter.armB")
        routed = 1 if arm_a else (2 if arm_b else 3)
        print(f"  parcel #{count}: barcode dest={dest}  ->  armA={arm_a} armB={arm_b}  ->  {CHUTE[routed]}")
        sim.clear_parcel()
        wait_until(lambda: plc.last_inputs.get("sensor.preDivert") is False)

    print()
    print(f"Throughput count : {gw.read_tag('throughput.count')}")
    print(f"Telemetry events : {tel.count()}")
    export_dir = os.path.join(_ROOT, "telemetry", "exports")
    for a in sys.argv[1:]:
        if a.startswith("--export-dir="):
            export_dir = a.split("=", 1)[1]
    out = tel.export_json(os.path.join(export_dir, "demo.json"))
    print(f"Telemetry export : {out}")

    tel.close()
    gw.close()
    plc.stop()


if __name__ == "__main__":
    main()
