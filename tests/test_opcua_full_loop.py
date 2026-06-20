"""End-to-end control loop over OPC UA (A7).

Proves the gateway is truly transport-agnostic: a full sorting cycle runs with the
TagGateway talking **OPC UA** to a server that mirrors the soft-PLC's process image.
The master writes sensors/inputs and reads actuators/counters entirely over OPC UA,
while the soft-PLC scans the in-process store. Per tick the bridge keeps the OPC UA
address space and the store in sync (`server_to_store` before the scan, `store_to_server`
after) — the role a real OPC-UA-enabled PLC's server plays. See ADR-0006.

OPTIONAL: requires `pip install asyncua`; skipped (exit 0) when it is absent — so the
zero-dependency suite stays green.

Dual-mode: runnable directly (`python tests/test_opcua_full_loop.py`) and via pytest.
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _sub in ("protocol-gateway", os.path.join("protocol-gateway", "adapters"),
             "plc", "telemetry", "simulation"):
    sys.path.insert(0, os.path.join(_ROOT, _sub))

try:
    import asyncua  # noqa: F401
    HAVE_ASYNCUA = True
except Exception:
    HAVE_ASYNCUA = False

ENDPOINT = "opc.tcp://127.0.0.1:48455/oltwin"
SIZE = 8
MVP_REGISTRY = os.path.join(_ROOT, "protocol-gateway", "config", "tags.sorting_cell_mvp.json")


def test_full_control_loop_over_opcua():
    if not HAVE_ASYNCUA:
        print("  [SKIP] test_full_control_loop_over_opcua (no asyncua)")
        return
    from tag_registry import TagRegistry
    from gateway import TagGateway
    from soft_plc import SoftPlc
    from opcua_adapter import (build_opcua_server, OpcUaClient,
                               server_to_store, store_to_server)
    import control_logic_mvp
    from scene_model import SceneModel, DEST_CHUTE_A

    registry = TagRegistry.from_file(MVP_REGISTRY)
    plc = SoftPlc(registry, scan_interval=0.0, control=control_logic_mvp)
    server, ns = build_opcua_server(endpoint=ENDPOINT, size=SIZE)
    client = OpcUaClient(ENDPOINT).connect()
    gw = TagGateway(registry, client)
    scene = SceneModel()
    try:
        gw.initialize_inputs()                       # zero the input image over OPC UA
        scene.spawn(DEST_CHUTE_A, "P1")
        inputs = {"input.start_pb": True, "input.stop_pb": False,
                  "input.reset_pb": False, "input.estop": False}
        motor_seen = False
        counted = 0
        for _ in range(80):
            stags = scene.sensor_tags()
            gw.write_tag("sensor.pe_001", stags["sensor.pe_001"])           # over OPC UA
            gw.write_tag("sensor.pe_002", stags["sensor.pe_002"])
            gw.write_tag("data.parcel_destination", stags["data.parcel_destination"])
            for name, value in inputs.items():
                gw.write_tag(name, value)
            server_to_store(server, ns, plc.store, SIZE)   # OPC UA -> process image
            plc.scan_once()                                # the PLC scans the store
            store_to_server(server, ns, plc.store, SIZE)   # process image -> OPC UA
            motor = bool(gw.read_tag("output.motor_conv_001_run"))          # over OPC UA
            divert = bool(gw.read_tag("output.diverter_dv_001_extend"))
            motor_seen = motor_seen or motor
            scene.step(0.05, motor, divert)
            inputs["input.start_pb"] = False               # momentary press
            counted = gw.read_tag("counter.sorted_chute_a")
            if counted >= 1:                               # cycle complete — stop early
                break
        assert motor_seen, "motor never energised over the OPC UA loop"
        assert list(scene.chute_a) == ["P1"], scene.chute_a
        assert gw.read_tag("counter.sorted_chute_a") == 1
        assert gw.read_tag("counter.sorted_chute_b") == 0
        print("  [PASS] full sorting cycle over OPC UA: P1 -> CHUTE_A, counter=1")
    finally:
        client.close()
        server.stop()
        plc.stop()


def _all_tests():
    return [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]


def main():
    for t in _all_tests():
        t()
    print("OPC UA full-loop tests: done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
