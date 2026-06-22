"""Live HMI server (V3): WebSocket protocol + real-time twin engine.

Verifies the hand-rolled RFC 6455 handshake + framing end-to-end (a raw client receives a
JSON frame and a command is accepted), and that the engine's commands actually drive the soft-PLC
control logic (start runs the motor, parcels sort, E-stop stops it, reset re-enables). Stdlib only;
runs in CI. Dual-mode: direct or pytest.
"""
import json
import os
import socket
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

from hmi_server import (HmiServer, TwinEngine,                      # noqa: E402
                        ws_handshake_client, ws_send, ws_recv)


def test_websocket_handshake_and_frame_shape():
    srv = HmiServer(TwinEngine(spawn_interval=0.3), "127.0.0.1", 0, dt=0.02)
    port = srv.serve()
    try:
        c = socket.create_connection(("127.0.0.1", port), timeout=3); c.settimeout(3)
        assert ws_handshake_client(c, "127.0.0.1"), "WebSocket handshake failed"
        m = ws_recv(c)
        assert m and m[0] == 0x1, "no text frame received"
        frame = json.loads(m[1].decode())
        assert {"t", "motor", "diverter", "jam", "estop", "a", "b", "pe1", "pe2", "parcels"} <= set(frame)
        ws_send(c, json.dumps({"cmd": "start"}), mask=True)   # masked client->server command
        m2 = ws_recv(c)
        assert m2 and m2[0] == 0x1, "stream stopped after a command"
        c.close()
    finally:
        srv.stop()


def test_engine_commands_drive_the_control_logic():
    eng = TwinEngine(spawn_interval=0.3)
    f = None
    for _ in range(5):
        f = eng.tick(0.05)
    assert not f["motor"], "motor should be off before Start"

    eng.command("start")
    assert any(eng.tick(0.05)["motor"] for _ in range(5)), "Start did not run the motor"

    sorted_any = False
    for _ in range(250):
        f = eng.tick(0.05)
        if f["a"] + f["b"] > 0:
            sorted_any = True
            break
    assert sorted_any, "no parcel sorted under live drive"

    eng.command("estop"); eng.tick(0.05)
    assert not eng.tick(0.05)["motor"], "E-stop did not stop the motor"

    eng.command("reset"); eng.command("start")
    assert any(eng.tick(0.05)["motor"] for _ in range(5)), "could not restart after Reset"


def test_stop_command_halts_the_motor():
    eng = TwinEngine(spawn_interval=0.3)
    eng.command("start")
    assert any(eng.tick(0.05)["motor"] for _ in range(5)), "Start did not run the motor"
    eng.command("stop"); eng.tick(0.05)
    assert not eng.tick(0.05)["motor"], "Stop pushbutton did not halt the motor"


def test_jam_injection_latches_alarm_and_reset_recovers():
    eng = TwinEngine(spawn_interval=0.3)
    eng.command("start")
    for _ in range(3):
        eng.tick(0.05)
    eng.command("jam")                       # stick a parcel blocking PE-002
    f = None
    for _ in range(80):                      # jam timer (~1 s) must trip
        f = eng.tick(0.05)
        if f["jam"]:
            break
    assert f["jam"], "injected jam did not raise alarm.jam_001"
    assert not f["motor"], "motor must stop while jammed"
    eng.command("reset"); eng.command("start")
    recovered = False
    for _ in range(10):
        f = eng.tick(0.05)
        if not f["jam"] and f["motor"]:
            recovered = True
            break
    assert recovered, "Reset did not clear the jam / allow the cell to restart"


def test_estop_appears_in_the_live_frame():
    eng = TwinEngine(spawn_interval=0.3)
    assert eng.tick(0.05)["estop"] is False, "estop should be clear initially"
    eng.command("estop")
    assert eng.tick(0.05)["estop"] is True, "E-stop must latch in the broadcast frame"
    eng.command("reset")
    assert eng.tick(0.05)["estop"] is False, "Reset must clear the latched E-stop"


def _all_tests():
    return [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]


def main():
    passed = 0
    for t in _all_tests():
        t(); print(f"  [PASS] {t.__name__}"); passed += 1
    print(f"HMI live-server tests: {passed} passed, 0 failed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
