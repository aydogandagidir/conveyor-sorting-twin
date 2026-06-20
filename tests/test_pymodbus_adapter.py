"""Protocol factory + adapters tests.

- Factory returns the right backend types; OPC UA / MQTT stubs raise NotImplementedError.
- pymodbus adapter interop: when pymodbus is installed, a real pymodbus master talks to
  the in-repo soft-PLC server (proving the server is standards-compliant and the gateway
  is transport-agnostic). Skips cleanly when pymodbus is absent, so the zero-dependency
  suite stays green.

Dual-mode: `python tests/test_pymodbus_adapter.py` (exit 0/1) or pytest.
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _sub in ("protocol-gateway", "plc", "telemetry", "simulation"):
    sys.path.insert(0, os.path.join(_ROOT, _sub))

from protocol_factory import make_client       # noqa: E402
from modbus_tcp import (                        # noqa: E402
    ModbusTCPClient, LocalStoreClient, ModbusDataStore, ModbusTCPServer,
)

MVP_REGISTRY = os.path.join(_ROOT, "protocol-gateway", "config", "tags.sorting_cell_mvp.json")

try:
    import pymodbus  # noqa: F401
    HAVE_PYMODBUS = True
except ImportError:
    HAVE_PYMODBUS = False


class _Skip(Exception):
    pass


def _skip_if_no_pymodbus():
    if HAVE_PYMODBUS:
        return
    if os.environ.get("PYTEST_CURRENT_TEST"):  # only when actually running under pytest
        import pytest
        pytest.skip("pymodbus not installed (optional backend)")
    raise _Skip()


# --- factory + stubs (no pymodbus needed) -----------------------------------
def test_factory_returns_inrepo_backends():
    assert isinstance(make_client("modbus", host="127.0.0.1", port=15502), ModbusTCPClient)
    assert isinstance(make_client("local", store=ModbusDataStore(8)), LocalStoreClient)


def test_factory_unknown_kind_raises():
    try:
        make_client("nope")
    except ValueError:
        return
    raise AssertionError("expected ValueError for unknown kind")


def test_mqtt_stub_raises():
    client = make_client("mqtt")
    try:
        client.connect()
    except NotImplementedError:
        return
    raise AssertionError("mqtt stub should raise NotImplementedError on connect()")


# --- pymodbus interop (skips without pymodbus) ------------------------------
def test_pymodbus_adapter_roundtrips():
    _skip_if_no_pymodbus()
    store = ModbusDataStore(64)
    srv = ModbusTCPServer(store, "127.0.0.1", 0).start()
    cli = make_client("pymodbus", host="127.0.0.1", port=srv.port).connect()
    try:
        cli.write_coil(3, True)
        assert cli.read_coils(3, 1) == [True]
        cli.write_register(2, 0xBEEF)
        assert cli.read_holding_registers(2, 1) == [0xBEEF]
        store.discrete_inputs[5] = True
        assert cli.read_discrete_inputs(5, 1) == [True]
        store.input_registers[1] = 4242
        assert cli.read_input_registers(1, 1) == [4242]
    finally:
        cli.close()
        srv.stop()


def test_pymodbus_through_gateway_runs_control_loop():
    _skip_if_no_pymodbus()
    from tag_registry import TagRegistry
    from gateway import TagGateway
    from soft_plc import SoftPlc
    import control_logic_mvp
    registry = TagRegistry.from_file(MVP_REGISTRY)
    plc = SoftPlc(registry, control=control_logic_mvp, scan_interval=0.0)
    port = plc.serve("127.0.0.1", 0)
    gw = TagGateway(registry, make_client("pymodbus", host="127.0.0.1", port=port)).connect()
    try:
        gw.initialize_inputs()
        gw.write_tag("input.start_pb", True)
        plc.scan_once()
        gw.write_tag("input.start_pb", False)
        plc.scan_once()
        assert gw.read_tag("output.motor_conv_001_run") is True
    finally:
        gw.close()
        plc.stop()


def _all_tests():
    return [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]


def main():
    passed = failed = skipped = 0
    for t in _all_tests():
        try:
            t()
            print(f"  [PASS] {t.__name__}")
            passed += 1
        except _Skip:
            print(f"  [SKIP] {t.__name__} (pymodbus not installed)")
            skipped += 1
        except AssertionError as e:
            print(f"  [FAIL] {t.__name__}: {e}")
            failed += 1
    print(f"\nprotocol factory/adapter tests: {passed} passed, {skipped} skipped, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
