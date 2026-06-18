"""Tests for the NC fail-safe E-stop via the tag `invert` flag (ADR-0004).

A real industrial E-stop is normally-closed (de-energize-to-trip): the wire is
TRUE when healthy and FALSE when pressed OR broken. Marking `input.estop` with
`invert: true` makes the soft-PLC present the logical engaged value to the control
program, so the SAME control_logic_mvp.py works with real NC wiring.

Dual-mode: `python tests/test_estop_failsafe.py` (exit 0/1) or pytest.
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _sub in ("protocol-gateway", "plc", "telemetry", "simulation"):
    sys.path.insert(0, os.path.join(_ROOT, _sub))

from tag_registry import TagRegistry      # noqa: E402
from modbus_tcp import LocalStoreClient    # noqa: E402
from gateway import TagGateway             # noqa: E402
from soft_plc import SoftPlc               # noqa: E402
import control_logic_mvp                   # noqa: E402


def _registry(invert_estop):
    return TagRegistry.from_dict({
        "version": "test", "cell": "estop_failsafe_test",
        "tags": [
            {"name": "sensor.pe_001", "type": "bool", "direction": "sim_to_plc", "role": "sensor", "modbus": {"table": "coil", "address": 0}},
            {"name": "sensor.pe_002", "type": "bool", "direction": "sim_to_plc", "role": "sensor", "modbus": {"table": "coil", "address": 1}},
            {"name": "input.start_pb", "type": "bool", "direction": "sim_to_plc", "role": "input", "modbus": {"table": "coil", "address": 2}},
            {"name": "input.stop_pb", "type": "bool", "direction": "sim_to_plc", "role": "input", "modbus": {"table": "coil", "address": 3}},
            {"name": "input.reset_pb", "type": "bool", "direction": "sim_to_plc", "role": "input", "modbus": {"table": "coil", "address": 4}},
            {"name": "input.estop", "type": "bool", "direction": "sim_to_plc", "role": "safety",
             "modbus": {"table": "coil", "address": 5}, "invert": invert_estop, "initial": bool(invert_estop)},
            {"name": "data.parcel_destination", "type": "uint16", "direction": "sim_to_plc", "role": "data", "modbus": {"table": "holding_register", "address": 0}},
            {"name": "output.motor_conv_001_run", "type": "bool", "direction": "plc_to_sim", "role": "actuator", "modbus": {"table": "discrete_input", "address": 0}},
            {"name": "output.diverter_dv_001_extend", "type": "bool", "direction": "plc_to_sim", "role": "actuator", "modbus": {"table": "discrete_input", "address": 1}},
            {"name": "alarm.jam_001", "type": "bool", "direction": "plc_to_sim", "role": "alarm", "modbus": {"table": "discrete_input", "address": 2}},
            {"name": "counter.sorted_chute_a", "type": "uint16", "direction": "plc_to_sim", "role": "counter", "modbus": {"table": "input_register", "address": 0}},
            {"name": "counter.sorted_chute_b", "type": "uint16", "direction": "plc_to_sim", "role": "counter", "modbus": {"table": "input_register", "address": 1}},
        ],
    })


def _start(gw, plc):
    gw.write_tag("input.start_pb", True)
    plc.scan_once()
    gw.write_tag("input.start_pb", False)
    plc.scan_once()


def test_failsafe_estop_runs_when_healthy_and_trips_when_deenergized():
    reg = _registry(invert_estop=True)
    plc = SoftPlc(reg, control=control_logic_mvp, scan_interval=0.0)
    gw = TagGateway(reg, LocalStoreClient(plc.store)).connect()
    gw.initialize_inputs()  # estop wire = True (healthy, NC closed)
    _start(gw, plc)
    assert gw.read_tag("output.motor_conv_001_run") is True, "healthy E-stop wire should permit running"
    # De-energize the E-stop line (button pressed OR wire broken) -> must stop.
    gw.write_tag("input.estop", False)
    plc.scan_once()
    assert gw.read_tag("output.motor_conv_001_run") is False, "de-energized E-stop must stop the motor (fail-safe)"
    plc.stop()


def test_active_true_estop_is_default_behaviour():
    # Without invert, the simulation convention is active-true (true = engaged).
    reg = _registry(invert_estop=False)
    plc = SoftPlc(reg, control=control_logic_mvp, scan_interval=0.0)
    gw = TagGateway(reg, LocalStoreClient(plc.store)).connect()
    gw.initialize_inputs()  # estop = False (not engaged)
    _start(gw, plc)
    assert gw.read_tag("output.motor_conv_001_run") is True
    gw.write_tag("input.estop", True)  # engage (active-true)
    plc.scan_once()
    assert gw.read_tag("output.motor_conv_001_run") is False
    plc.stop()


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
    print(f"\nE-stop fail-safe tests: {passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
