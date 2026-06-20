"""MQTT telemetry publisher tests.

- Topic/payload formatting and the TelemetryLogger `sink` hook are pure — verified with no
  broker and no paho-mqtt.
- A real publish/subscribe round-trip runs only when paho-mqtt is installed AND a broker is
  reachable (set MQTT_HOST), so the zero-dependency suite stays green.

Dual-mode: `python tests/test_mqtt_telemetry.py` (exit 0/1) or pytest.
"""
import json
import os
import sys
import tempfile
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _sub in ("telemetry", "scripts", "protocol-gateway", "plc", "simulation"):
    sys.path.insert(0, os.path.join(_ROOT, _sub))

from mqtt_publisher import MqttTelemetryPublisher  # noqa: E402
from telemetry_logger import TelemetryLogger        # noqa: E402

try:
    import paho.mqtt.client as _mqtt  # noqa: F401
    HAVE_PAHO = True
except ImportError:
    HAVE_PAHO = False

MQTT_HOST = os.environ.get("MQTT_HOST")


class _Skip(Exception):
    pass


def _skip_if_no_broker():
    if HAVE_PAHO and MQTT_HOST:
        return
    reason = "paho-mqtt + a reachable broker (set MQTT_HOST) required"
    if os.environ.get("PYTEST_CURRENT_TEST"):
        import pytest
        pytest.skip(reason)
    raise _Skip()


def _tmp_db():
    return os.path.join(tempfile.mkdtemp(prefix="oltwin_mqtt_"), "telemetry.db")


# --- pure: no paho, no broker -----------------------------------------------
def test_topic_and_payload_format():
    pub = MqttTelemetryPublisher(topic_prefix="openlogitwin")
    event = {"scenario": "jam_recovery_basic", "event_type": "fault",
             "tag": "alarm.jam_001", "value": "True", "detail": "t=3.05"}
    assert pub.topic_for(event) == "openlogitwin/jam_recovery_basic/fault"
    assert json.loads(pub.payload_for(event))["tag"] == "alarm.jam_001"
    # odd characters in scenario / event_type are sanitised into one segment each
    assert pub.topic_for({"scenario": "a/b c", "event_type": "x#y"}) == "openlogitwin/a_b_c/x_y"


def test_telemetry_sink_receives_events():
    collected = []
    tel = TelemetryLogger(_tmp_db(), scenario="sinktest", sink=collected.append)
    tel.log_event("machine_state", tag="motor_run", detail="t=0")
    tel.log_sort("CHUTE_A", 1, detail="count=1")
    tel.close()
    assert len(collected) == 2
    assert collected[0]["event_type"] == "machine_state" and collected[0]["scenario"] == "sinktest"
    assert collected[1]["event_type"] == "sort" and collected[1]["tag"] == "CHUTE_A"


def test_sink_failure_does_not_crash_logging():
    def boom(_event):
        raise RuntimeError("sink down")
    tel = TelemetryLogger(_tmp_db(), sink=boom)
    tel.log_event("cycle", tag="x")   # must not raise despite the failing sink
    assert tel.count() == 1           # the SQLite write still happened
    tel.close()


def test_scenario_run_forwards_telemetry_to_sink():
    # The CLI wires --mqtt-host -> publisher.as_sink() -> ScenarioRunner -> TelemetryLogger.
    # Here a list sink proves the whole thread end to end (no broker needed).
    import scenario_manager
    collected = []
    path = scenario_manager.resolve("barcode_sorting_basic")
    scenario_manager.run_and_check(path, use_modbus=False, telemetry_sink=collected.append)
    assert collected, "no telemetry reached the sink"
    assert all("event_type" in e and "scenario" in e for e in collected)
    assert any(e["event_type"] == "sort" for e in collected)


# --- real round-trip: skips without paho + broker ---------------------------
def test_mqtt_publish_subscribe_roundtrip():
    _skip_if_no_broker()
    import paho.mqtt.client as mqtt
    host, port = MQTT_HOST, int(os.environ.get("MQTT_PORT", "1883"))
    received = []
    try:
        sub = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="oltwin-sub")
    except (AttributeError, TypeError):
        sub = mqtt.Client(client_id="oltwin-sub")
    sub.on_message = lambda c, u, msg: received.append((msg.topic, msg.payload.decode()))
    sub.connect(host, port)
    sub.subscribe("openlogitwin/#")
    sub.loop_start()
    pub = MqttTelemetryPublisher(host=host, port=port).connect()
    try:
        pub.publish({"scenario": "rt", "event_type": "sort", "tag": "CHUTE_A", "value": "1"})
        end = time.time() + 5.0
        while time.time() < end and not received:
            time.sleep(0.05)
        topics = [t for t, _ in received]
        assert "openlogitwin/rt/sort" in topics, f"got {topics}"
    finally:
        pub.close()
        sub.loop_stop()
        sub.disconnect()


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
            print(f"  [SKIP] {t.__name__} (no paho-mqtt/broker)")
            skipped += 1
        except AssertionError as e:
            print(f"  [FAIL] {t.__name__}: {e}")
            failed += 1
    print(f"\nMQTT telemetry tests: {passed} passed, {skipped} skipped, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
