"""Modbus robustness (A8): auto-reconnect + multi-word register types.

- `ModbusTCPClient` transparently reconnects and retries after a dropped socket.
- `uint32` / `float32` tags round-trip across two 16-bit registers through the gateway.

Stdlib only; exercises the in-repo Modbus server. Dual-mode: direct or pytest.
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "protocol-gateway"))

from modbus_tcp import (ModbusDataStore, ModbusTCPServer, ModbusTCPClient,  # noqa: E402
                        encode_registers, decode_registers)
from tag_registry import TagRegistry  # noqa: E402
from gateway import TagGateway        # noqa: E402


def test_codec_roundtrip():
    assert decode_registers("uint16", encode_registers("uint16", 40000)) == 40000
    assert decode_registers("uint32", encode_registers("uint32", 300000)) == 300000
    assert abs(decode_registers("float32", encode_registers("float32", 3.14159)) - 3.14159) < 1e-4
    assert len(encode_registers("uint32", 1)) == 2      # spans two registers
    assert len(encode_registers("uint16", 1)) == 1


def test_client_reconnects_after_dropped_socket():
    store = ModbusDataStore()
    store.holding_registers[0] = 4242
    server = ModbusTCPServer(store, "127.0.0.1", 0).start()
    try:
        client = ModbusTCPClient("127.0.0.1", server.port).connect()
        assert client.read_holding_registers(0, 1) == [4242]
        client._sock.close()                            # simulate a dropped connection
        # the next request must transparently reconnect and still return the value
        assert client.read_holding_registers(0, 1) == [4242]
        client.close()
    finally:
        server.stop()


def test_multiword_tags_roundtrip_over_modbus():
    reg = TagRegistry.from_dict({"cell": "test", "tags": [
        {"name": "data.total", "type": "uint32", "direction": "sim_to_plc", "role": "data",
         "modbus": {"table": "holding_register", "address": 10}},
        {"name": "data.rate", "type": "float32", "direction": "sim_to_plc", "role": "data",
         "modbus": {"table": "holding_register", "address": 12}},
    ]})
    store = ModbusDataStore()
    server = ModbusTCPServer(store, "127.0.0.1", 0).start()
    try:
        gw = TagGateway(reg, ModbusTCPClient("127.0.0.1", server.port).connect())
        gw.write_tag("data.total", 300000)              # > 65535, needs two registers
        gw.write_tag("data.rate", 12.5)
        assert gw.read_tag("data.total") == 300000
        assert abs(gw.read_tag("data.rate") - 12.5) < 1e-5
        # the value physically occupies two consecutive registers in the slave's image
        assert (store.holding_registers[10], store.holding_registers[11]) != (0, 0)
        gw.close()
    finally:
        server.stop()


def _all_tests():
    return [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]


def main():
    passed = 0
    for t in _all_tests():
        t(); print(f"  [PASS] {t.__name__}"); passed += 1
    print(f"modbus robustness tests: {passed} passed, 0 failed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
