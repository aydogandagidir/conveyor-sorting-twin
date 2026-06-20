"""OPC UA adapter tests (second protocol priority) — skip-by-default.

When `asyncua` is installed, this stands up an in-process OPC UA server and drives it through
the OpenLogiTwin client interface and the TagGateway — proving the gateway is transport-agnostic
over OPC UA, not just Modbus. Skips cleanly when asyncua is absent, so the zero-dependency suite
stays green.

Dual-mode: `python tests/test_opcua_adapter.py` (exit 0/1) or pytest.
"""
import contextlib
import os
import socket
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _sub in ("protocol-gateway", "plc", "telemetry", "simulation"):
    sys.path.insert(0, os.path.join(_ROOT, _sub))

from protocol_factory import make_client  # noqa: E402

MVP_REGISTRY = os.path.join(_ROOT, "protocol-gateway", "config", "tags.sorting_cell_mvp.json")

try:
    import asyncua  # noqa: F401
    HAVE_ASYNCUA = True
except ImportError:
    HAVE_ASYNCUA = False


class _Skip(Exception):
    pass


def _skip_if_no_asyncua():
    if HAVE_ASYNCUA:
        return
    if os.environ.get("PYTEST_CURRENT_TEST"):
        import pytest
        pytest.skip("asyncua not installed (optional backend)")
    raise _Skip()


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@contextlib.contextmanager
def _server_and_client():
    from adapters.opcua_adapter import build_opcua_server
    endpoint = f"opc.tcp://127.0.0.1:{_free_port()}/oltwin"
    server, ns = build_opcua_server(endpoint)
    client = make_client("opcua", endpoint=endpoint).connect()
    try:
        yield server, ns, client
    finally:
        client.close()
        server.stop()


def test_opcua_roundtrips_all_tables():
    _skip_if_no_asyncua()
    from adapters.opcua_adapter import server_set
    with _server_and_client() as (server, ns, cli):
        cli.write_coil(3, True)
        assert cli.read_coils(3, 1) == [True]
        cli.write_register(2, 0xBEEF)
        assert cli.read_holding_registers(2, 1) == [0xBEEF]
        server_set(server, ns, "discrete_input", 5, True)   # simulate a PLC output
        assert cli.read_discrete_inputs(5, 1) == [True]
        server_set(server, ns, "input_register", 1, 4242)
        assert cli.read_input_registers(1, 1) == [4242]


def test_gateway_runs_over_opcua():
    _skip_if_no_asyncua()
    from tag_registry import TagRegistry
    from gateway import TagGateway
    from adapters.opcua_adapter import server_set
    registry = TagRegistry.from_file(MVP_REGISTRY)
    with _server_and_client() as (server, ns, cli):
        gw = TagGateway(registry, cli)
        gw.write_tag("sensor.pe_001", True)
        gw.write_tag("data.parcel_destination", 2)
        assert gw.read_tag("sensor.pe_001") is True
        assert gw.read_tag("data.parcel_destination") == 2
        server_set(server, ns, "discrete_input", 0, True)   # motor.conveyor
        assert gw.read_tag("output.motor_conv_001_run") is True


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
            print(f"  [SKIP] {t.__name__} (asyncua not installed)")
            skipped += 1
        except AssertionError as e:
            print(f"  [FAIL] {t.__name__}: {e}")
            failed += 1
    print(f"\nOPC UA adapter tests: {passed} passed, {skipped} skipped, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
