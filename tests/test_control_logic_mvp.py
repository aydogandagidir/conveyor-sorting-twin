"""Unit tests for plc/control_logic_mvp.py — the pure scan() control program.

These exercise the control logic in isolation (no Modbus, no scene), covering
edge cases the end-to-end scenarios do not: stop button alone, reset without jam,
jam blocks start, E-stop clears the diverter latch, pending cleared on reset.

Dual-mode: runnable directly (`python tests/test_control_logic_mvp.py`, exit 0/1)
and collectable by pytest (test_* functions with asserts).
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "plc"))

import control_logic_mvp as C  # noqa: E402


def I(**kw):
    base = {
        "sensor.pe_001": False, "sensor.pe_002": False,
        "input.start_pb": False, "input.stop_pb": False,
        "input.reset_pb": False, "input.estop": False,
        "data.parcel_destination": 0,
    }
    base.update(kw)
    return base


def run(seq):
    st = C.initial_state()
    outs = []
    for inp in seq:
        out, st = C.scan(inp, st)
        outs.append(out)
    return outs, st


def test_idle_without_start_motor_off():
    outs, st = run([I(), I()])
    assert outs[-1]["output.motor_conv_001_run"] is False
    assert st["running"] is False


def test_start_latches_motor_and_holds_after_release():
    outs, _ = run([I(**{"input.start_pb": True}), I()])
    assert outs[0]["output.motor_conv_001_run"] is True
    assert outs[1]["output.motor_conv_001_run"] is True  # holds after release


def test_stop_button_drops_running():
    outs, st = run([I(**{"input.start_pb": True}), I(), I(**{"input.stop_pb": True}), I()])
    assert outs[1]["output.motor_conv_001_run"] is True
    assert outs[3]["output.motor_conv_001_run"] is False
    assert st["running"] is False


def test_estop_overrides_running():
    outs, st = run([I(**{"input.start_pb": True}), I(**{"input.estop": True}), I()])
    assert outs[0]["output.motor_conv_001_run"] is True
    assert outs[1]["output.motor_conv_001_run"] is False
    assert outs[2]["output.motor_conv_001_run"] is False  # stays off until re-start


def test_routing_dest_a_extends_diverter_and_counts_on_exit():
    seq = [
        I(**{"input.start_pb": True}),
        I(),
        I(**{"sensor.pe_002": True, "data.parcel_destination": 1}),  # rising -> divert A
        I(**{"sensor.pe_002": True, "data.parcel_destination": 1}),
        I(**{"data.parcel_destination": 1}),                         # falling -> count A
    ]
    outs, st = run(seq)
    assert outs[2]["output.diverter_dv_001_extend"] is True
    assert st["count_a"] == 1 and st["count_b"] == 0
    assert outs[-1]["counter.sorted_chute_a"] == 1


def test_routing_dest_b_no_extend_and_counts_b():
    seq = [
        I(**{"input.start_pb": True}),
        I(),
        I(**{"sensor.pe_002": True, "data.parcel_destination": 2}),
        I(**{"sensor.pe_002": True, "data.parcel_destination": 2}),
        I(**{"data.parcel_destination": 2}),
    ]
    outs, st = run(seq)
    assert outs[2]["output.diverter_dv_001_extend"] is False
    assert st["count_b"] == 1 and st["count_a"] == 0


def test_jam_latches_after_limit_and_stops_motor():
    seq = [I(**{"input.start_pb": True})] + [I(**{"sensor.pe_002": True}) for _ in range(C.JAM_SCAN_LIMIT)]
    outs, st = run(seq)
    assert st["jam"] is True
    assert outs[-1]["alarm.jam_001"] is True
    assert outs[-1]["output.motor_conv_001_run"] is False


def test_reset_clears_jam_and_allows_restart():
    seq = [I(**{"input.start_pb": True})] + [I(**{"sensor.pe_002": True}) for _ in range(C.JAM_SCAN_LIMIT)]
    seq += [I(**{"input.reset_pb": True}), I(**{"input.start_pb": True})]
    outs, st = run(seq)
    assert st["jam"] is False
    assert outs[-1]["output.motor_conv_001_run"] is True


def test_jam_blocks_start():
    seq = [I(**{"input.start_pb": True})] + [I(**{"sensor.pe_002": True}) for _ in range(C.JAM_SCAN_LIMIT)]
    seq += [I(**{"input.start_pb": True, "sensor.pe_002": True})]  # try start while jammed
    outs, st = run(seq)
    assert st["jam"] is True
    assert outs[-1]["output.motor_conv_001_run"] is False


def test_reset_without_jam_is_safe():
    outs, st = run([I(**{"input.reset_pb": True}), I()])
    assert st["jam"] is False
    assert outs[-1]["output.motor_conv_001_run"] is False  # reset does not start the motor


def test_estop_clears_diverter_latch():
    seq = [
        I(**{"input.start_pb": True}),
        I(**{"sensor.pe_002": True, "data.parcel_destination": 1}),  # divert latched True
        I(**{"input.estop": True, "sensor.pe_002": True, "data.parcel_destination": 1}),
    ]
    outs, st = run(seq)
    assert outs[1]["output.diverter_dv_001_extend"] is True
    assert outs[2]["output.diverter_dv_001_extend"] is False
    assert st["divert"] is False  # latch explicitly cleared on E-stop (safety)


def test_pending_cleared_on_reset_prevents_phantom_count():
    seq = [
        I(**{"input.start_pb": True}),
        I(**{"sensor.pe_002": True, "data.parcel_destination": 1}),  # rising -> pending A
        I(**{"input.reset_pb": True}),                               # reset clears pending
        I(),                                                         # pe_002 falling, but no pending
    ]
    outs, st = run(seq)
    assert st["count_a"] == 0 and st["count_b"] == 0


def test_jammed_parcel_is_never_counted():
    # rising edge sets pending, but pe_002 stays blocked (jam) -> no falling edge -> no count
    seq = [I(**{"input.start_pb": True})] + [I(**{"sensor.pe_002": True, "data.parcel_destination": 1})
                                             for _ in range(C.JAM_SCAN_LIMIT + 2)]
    outs, st = run(seq)
    assert st["jam"] is True
    assert st["count_a"] == 0


def test_counter_wraps_at_uint16():
    # The uint16 counter output wraps at 65536 (matches the Modbus input register),
    # even though the internal running total keeps counting.
    st = C.initial_state()
    st["running"] = True
    st["count_a"] = 65535
    st["pending"] = C.DEST_CHUTE_A
    st["prev_pe_002"] = True                      # pe_002 False below = falling edge -> count
    out, st = C.scan(I(**{"sensor.pe_002": False}), st)
    assert st["count_a"] == 65536
    assert out["counter.sorted_chute_a"] == 0


def _all_tests():
    return [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]


def main():
    passed = 0
    failed = 0
    for t in _all_tests():
        try:
            t()
            print(f"  [PASS] {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  [FAIL] {t.__name__}: {e}")
            failed += 1
    print(f"\ncontrol_logic_mvp unit tests: {passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
