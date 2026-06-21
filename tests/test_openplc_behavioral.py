"""OpenPLC behavioural-equivalence test (skip-by-default).

Drives a REAL OpenPLC running `plc/examples/03_sorting_cell_commissioning.st` over
Modbus and asserts it sorts identically to the Python soft-PLC (`control_logic_mvp`).
This is the "full behavioural" check beyond the reachability smoke test — possible
because the commissioning ST maps every PLC input to a master-writable coil/register.

Precondition (manual, like a real PLC): load + compile + start
`03_sorting_cell_commissioning.st` on an OpenPLC reachable at OPENPLC_HOST/OPENPLC_PORT.
Skips cleanly when OPENPLC_HOST is unset, so the zero-dependency suite stays green.

Verified 2026-06-20 against OpenPLC Runtime v3 (Docker). Dual-mode: direct or pytest.
"""
import os
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "protocol-gateway"))
sys.path.insert(0, os.path.join(_ROOT, "plc"))

HAVE_OPENPLC = bool(os.environ.get("OPENPLC_HOST"))

# Commissioning Modbus map (OpenPLC: %QX->coils, %QW->holding regs).
MOTOR, DIVERTER, JAM = 0, 1, 2                       # outputs (read)
PE1, PE2, START, STOP, RESET, ESTOP = 8, 9, 10, 11, 12, 13   # inputs (write)
HR_COUNT_A, HR_BARCODE, HR_COUNT_B = 0, 1, 2


class _Skip(Exception):
    pass


def _skip_if_no_openplc():
    if HAVE_OPENPLC:
        return
    if os.environ.get("PYTEST_CURRENT_TEST"):
        import pytest
        pytest.skip("OPENPLC_HOST not set (live OpenPLC + commissioning program required)")
    raise _Skip()


def _soft_plc_reference():
    """Run control_logic_mvp through the same logical sequence: parcel A then parcel B."""
    import control_logic_mvp as C
    st = C.initial_state()

    def scan(**kw):
        nonlocal st
        base = {"sensor.pe_001": False, "sensor.pe_002": False, "input.start_pb": False,
                "input.stop_pb": False, "input.reset_pb": False, "input.estop": False,
                "data.parcel_destination": 0}
        base.update(kw)
        out, st = C.scan(base, st)
        return out

    scan(**{"input.start_pb": True}); scan()
    scan(**{"sensor.pe_002": True, "data.parcel_destination": 1})
    scan(**{"sensor.pe_002": True, "data.parcel_destination": 1}); scan()
    scan(**{"sensor.pe_002": True, "data.parcel_destination": 2})
    scan(**{"sensor.pe_002": True, "data.parcel_destination": 2})
    out = scan()
    return {"motor": bool(out["output.motor_conv_001_run"]),
            "count_a": out["counter.sorted_chute_a"], "count_b": out["counter.sorted_chute_b"]}


def _drive_openplc():
    from modbus_tcp import ModbusTCPClient
    host = os.environ["OPENPLC_HOST"]
    port = int(os.environ.get("OPENPLC_PORT", "502"))
    c = ModbusTCPClient(host, port, timeout=5.0).connect()
    settle = lambda: time.sleep(0.2)
    try:
        # idempotent preamble: clean control state + zero the counters (%QW are master-writable)
        c.write_coil(STOP, True); settle(); c.write_coil(STOP, False)
        c.write_coil(RESET, True); settle(); c.write_coil(RESET, False); settle()
        c.write_register(HR_COUNT_A, 0); c.write_register(HR_COUNT_B, 0); settle()
        c.write_coil(ESTOP, True); settle()                 # NC fail-safe healthy
        c.write_coil(START, True); settle(); c.write_coil(START, False); settle()
        motor = c.read_coils(MOTOR, 1)[0]
        c.write_register(HR_BARCODE, 1); c.write_coil(PE2, True); settle()
        div_a = c.read_coils(DIVERTER, 1)[0]; c.write_coil(PE2, False); settle()
        c.write_register(HR_BARCODE, 2); c.write_coil(PE2, True); settle()
        div_b = c.read_coils(DIVERTER, 1)[0]; c.write_coil(PE2, False); settle()
        return {"motor": motor, "div_a": div_a, "div_b": div_b,
                "count_a": c.read_holding_registers(HR_COUNT_A, 1)[0],
                "count_b": c.read_holding_registers(HR_COUNT_B, 1)[0]}
    finally:
        c.close()


def test_openplc_matches_soft_plc():
    _skip_if_no_openplc()
    plc = _drive_openplc()
    ref = _soft_plc_reference()
    assert plc["motor"] is True, plc
    assert plc["div_a"] is True and plc["div_b"] is False, plc      # A routed, B straight
    assert plc["count_a"] == ref["count_a"] == 1, (plc, ref)
    assert plc["count_b"] == ref["count_b"] == 1, (plc, ref)


def _all_tests():
    return [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]


def main():
    passed = skipped = failed = 0
    for t in _all_tests():
        try:
            t(); print(f"  [PASS] {t.__name__}"); passed += 1
        except _Skip:
            print(f"  [SKIP] {t.__name__} (OPENPLC_HOST not set)"); skipped += 1
        except AssertionError as e:
            print(f"  [FAIL] {t.__name__}: {e}"); failed += 1
    print(f"\nOpenPLC behavioural: {passed} passed, {skipped} skipped, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
