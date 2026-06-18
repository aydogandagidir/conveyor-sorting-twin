"""Modbus TCP protocol tests — round-trips, batch function codes, and exception paths.

Exercises modbus_tcp.py over real TCP (not LocalStoreClient): FC 01-06/0F/10 and the
exception responses (ILLEGAL_FUNCTION / DATA_ADDRESS / DATA_VALUE) that the Phase 0/1
verifications never trigger.

Dual-mode: `python tests/test_modbus_protocol.py` (exit 0/1) or pytest.
"""
import contextlib
import os
import struct
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "protocol-gateway"))

import modbus_tcp as M  # noqa: E402
from modbus_tcp import (  # noqa: E402
    ModbusDataStore, ModbusTCPServer, ModbusTCPClient, ModbusError,
    ILLEGAL_FUNCTION, ILLEGAL_DATA_ADDRESS, ILLEGAL_DATA_VALUE,
)


@contextlib.contextmanager
def server_client(size=16):
    store = ModbusDataStore(size=size)
    srv = ModbusTCPServer(store, "127.0.0.1", 0).start()
    cli = ModbusTCPClient("127.0.0.1", srv.port).connect()
    try:
        yield store, cli
    finally:
        cli.close()
        srv.stop()


def _expect(exc_code, fn):
    try:
        fn()
    except ModbusError as e:
        assert e.exception_code == exc_code, f"got exception code {e.exception_code:#x}, want {exc_code:#x}"
        return
    raise AssertionError(f"expected ModbusError {exc_code:#x}, none raised")


# --- round-trips ------------------------------------------------------------
def test_coil_roundtrip():
    with server_client() as (_store, cli):
        cli.write_coil(3, True)
        assert cli.read_coils(3, 1) == [True]
        cli.write_coil(3, False)
        assert cli.read_coils(3, 1) == [False]


def test_register_roundtrip():
    with server_client() as (_store, cli):
        cli.write_register(2, 0xBEEF)
        assert cli.read_holding_registers(2, 1) == [0xBEEF]


def test_read_discrete_inputs():
    with server_client() as (store, cli):
        store.discrete_inputs[5] = True
        assert cli.read_discrete_inputs(5, 1) == [True]
        assert cli.read_discrete_inputs(4, 2) == [False, True]


def test_read_input_registers():
    with server_client() as (store, cli):
        store.input_registers[1] = 4242
        assert cli.read_input_registers(1, 1) == [4242]


def test_write_multiple_coils_roundtrip():
    with server_client() as (_store, cli):
        # FC 0x0F: addr 0, count 3, values [T, F, T] -> 0b00000101
        cli._request(M.WRITE_MULTIPLE_COILS, struct.pack(">HHB", 0, 3, 1) + bytes([0x05]))
        assert cli.read_coils(0, 3) == [True, False, True]


def test_write_multiple_registers_roundtrip():
    with server_client() as (_store, cli):
        # FC 0x10: addr 0, count 2, values [0x1234, 0x5678]
        cli._request(M.WRITE_MULTIPLE_REGISTERS, struct.pack(">HHB", 0, 2, 4) + struct.pack(">HH", 0x1234, 0x5678))
        assert cli.read_holding_registers(0, 2) == [0x1234, 0x5678]


# --- exception paths --------------------------------------------------------
def test_illegal_data_address_on_read():
    with server_client(size=16) as (_store, cli):
        _expect(ILLEGAL_DATA_ADDRESS, lambda: cli.read_coils(1000, 1))


def test_illegal_data_address_on_write():
    with server_client(size=16) as (_store, cli):
        _expect(ILLEGAL_DATA_ADDRESS, lambda: cli.write_register(1000, 1))


def test_illegal_data_value_count_too_large():
    with server_client() as (_store, cli):
        _expect(ILLEGAL_DATA_VALUE, lambda: cli.read_coils(0, 3000))  # > 2000


def test_illegal_data_value_bad_coil():
    with server_client() as (_store, cli):
        # Write Single Coil with an out-of-spec value (must be 0x0000 or 0xFF00).
        _expect(ILLEGAL_DATA_VALUE, lambda: cli._request(M.WRITE_SINGLE_COIL, struct.pack(">HH", 0, 0x1234)))


def test_illegal_function():
    with server_client() as (_store, cli):
        _expect(ILLEGAL_FUNCTION, lambda: cli._request(0x08, b"\x00\x00"))  # FC 0x08 not implemented


def test_connection_survives_exception():
    with server_client() as (_store, cli):
        _expect(ILLEGAL_DATA_ADDRESS, lambda: cli.read_coils(1000, 1))
        cli.write_coil(1, True)               # same connection still usable
        assert cli.read_coils(1, 1) == [True]


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
    print(f"\nModbus protocol tests: {passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
