"""Phase 1.5f prototype: per-parcel destination via a FIFO ring (see adr/0005).

Demonstrates that densely-spaced parcels (several in flight between pe_001 and the
diverter) are routed correctly when destinations are delivered through a ring of
registers (control_logic_advanced), whereas the single shared register
(control_logic_mvp) mis-routes them. Runs through the real stack
(SceneModel <-> gateway <-> SoftPlc).

Dual-mode: `python tests/test_multi_parcel_prototype.py` (exit 0/1) or pytest.
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _sub in ("protocol-gateway", "plc", "telemetry", "simulation"):
    sys.path.insert(0, os.path.join(_ROOT, _sub))

from tag_registry import TagRegistry          # noqa: E402
from modbus_tcp import LocalStoreClient         # noqa: E402
from gateway import TagGateway                  # noqa: E402
from soft_plc import SoftPlc                    # noqa: E402
from scene_model import SceneModel, DEST_CHUTE_A, DEST_CHUTE_B  # noqa: E402
import control_logic_advanced                   # noqa: E402
import control_logic_mvp                         # noqa: E402

RING = control_logic_advanced.RING_SIZE
DEST = {"A": DEST_CHUTE_A, "B": DEST_CHUTE_B}
PLAN = ("A", "B", "A", "A", "B", "B", "A", "B", "A", "B", "B", "A")  # 6 A, 6 B
MVP_REGISTRY = os.path.join(_ROOT, "protocol-gateway", "config", "tags.sorting_cell_mvp.json")


def _advanced_registry():
    tags = [
        {"name": "sensor.pe_001", "type": "bool", "direction": "sim_to_plc", "role": "sensor", "modbus": {"table": "coil", "address": 0}},
        {"name": "sensor.pe_002", "type": "bool", "direction": "sim_to_plc", "role": "sensor", "modbus": {"table": "coil", "address": 1}},
        {"name": "input.start_pb", "type": "bool", "direction": "sim_to_plc", "role": "input", "modbus": {"table": "coil", "address": 2}},
        {"name": "input.stop_pb", "type": "bool", "direction": "sim_to_plc", "role": "input", "modbus": {"table": "coil", "address": 3}},
        {"name": "input.reset_pb", "type": "bool", "direction": "sim_to_plc", "role": "input", "modbus": {"table": "coil", "address": 4}},
        {"name": "input.estop", "type": "bool", "direction": "sim_to_plc", "role": "safety", "modbus": {"table": "coil", "address": 5}},
    ]
    for i in range(RING):
        tags.append({"name": f"data.dest_ring_{i}", "type": "uint16", "direction": "sim_to_plc",
                     "role": "data", "modbus": {"table": "holding_register", "address": i}})
    tags += [
        {"name": "output.motor_conv_001_run", "type": "bool", "direction": "plc_to_sim", "role": "actuator", "modbus": {"table": "discrete_input", "address": 0}},
        {"name": "output.diverter_dv_001_extend", "type": "bool", "direction": "plc_to_sim", "role": "actuator", "modbus": {"table": "discrete_input", "address": 1}},
        {"name": "alarm.jam_001", "type": "bool", "direction": "plc_to_sim", "role": "alarm", "modbus": {"table": "discrete_input", "address": 2}},
        {"name": "counter.sorted_chute_a", "type": "uint16", "direction": "plc_to_sim", "role": "counter", "modbus": {"table": "input_register", "address": 0}},
        {"name": "counter.sorted_chute_b", "type": "uint16", "direction": "plc_to_sim", "role": "counter", "modbus": {"table": "input_register", "address": 1}},
    ]
    return TagRegistry.from_dict({"version": "proto", "cell": "sorting_cell_advanced", "tags": tags})


def _run_dense(registry, control, mode, spacing_s=0.4):
    """Drive PLAN parcels spaced spacing_s apart; return (expected, routed, counts)."""
    dt = 0.05
    scene = SceneModel()  # speed 50, len 10, pe1@20 pe2@80 divert@90 end@120
    plc = SoftPlc(registry, control=control, scan_interval=0.0)
    gw = TagGateway(registry, LocalStoreClient(plc.store)).connect()
    gw.initialize_inputs()
    gw.write_tag("input.start_pb", True)
    plc.scan_once()
    gw.write_tag("input.start_pb", False)
    plc.scan_once()

    spacing = int(round(spacing_s / dt))
    first = 10
    spawn_at = {first + i * spacing: (f"P{i + 1}", DEST[PLAN[i]]) for i in range(len(PLAN))}
    expected = {f"P{i + 1}": PLAN[i] for i in range(len(PLAN))}
    nsteps = first + len(PLAN) * spacing + int(round((120 / 50) / dt)) + 40
    write_idx = 0

    for k in range(nsteps):
        if k in spawn_at:
            pid, dest = spawn_at[k]
            scene.spawn(dest, pid)
        stags = scene.sensor_tags()
        gw.write_tag("sensor.pe_001", stags["sensor.pe_001"])
        gw.write_tag("sensor.pe_002", stags["sensor.pe_002"])
        if mode == "single":
            gw.write_tag("data.parcel_destination", stags["data.parcel_destination"])
        plc.scan_once()
        motor = gw.read_tag("output.motor_conv_001_run")
        divert = gw.read_tag("output.diverter_dv_001_extend")
        events = scene.step(dt, motor, divert)
        if mode == "ring":
            for ev in events:
                if ev[0] == "scan":
                    _, _pid, dest = ev
                    gw.write_tag(f"data.dest_ring_{write_idx % RING}", dest)
                    write_idx += 1

    counts = (gw.read_tag("counter.sorted_chute_a"), gw.read_tag("counter.sorted_chute_b"))
    routed = {}
    for pid in scene.chute_a:
        routed[pid] = "A"
    for pid in scene.chute_b:
        routed[pid] = "B"
    gw.close()
    plc.stop()
    return expected, routed, counts


def test_fifo_ring_routes_all_dense_parcels_correctly():
    expected, routed, (ca, cb) = _run_dense(_advanced_registry(), control_logic_advanced, "ring")
    assert len(routed) == len(PLAN), f"not all parcels routed: {routed}"
    wrong = {pid: routed.get(pid) for pid in expected if routed.get(pid) != expected[pid]}
    assert not wrong, f"FIFO ring mis-routed: {wrong}"
    assert ca == PLAN.count("A") and cb == PLAN.count("B"), f"counts A/B = {ca}/{cb}"


def test_single_register_misroutes_dense_parcels():
    # Same dense spacing through the single shared register -> at least one mis-route.
    expected, routed, _counts = _run_dense(
        TagRegistry.from_file(MVP_REGISTRY), control_logic_mvp, "single")
    correct = sum(1 for pid in expected if routed.get(pid) == expected[pid])
    assert correct < len(PLAN), (
        "single shared register unexpectedly routed every dense parcel correctly; "
        "the FIFO prototype would not be needed")


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
    print(f"\nmulti-parcel prototype tests: {passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
