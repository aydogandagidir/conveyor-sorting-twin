"""MQTT telemetry publisher (third protocol priority).

Publishes telemetry events to an MQTT broker — one topic per scenario + event type, JSON
payload. This is MQTT as a **telemetry sink**, not a gateway transport: MQTT is pub/sub, not
request/response, so the gateway stays on Modbus / OPC UA. Plug it into TelemetryLogger via
`sink=publisher.as_sink()`.

`paho-mqtt` is imported lazily (optional dependency). The topic/payload formatting is pure and
testable without a broker; a real publish/subscribe round-trip needs paho-mqtt + a reachable
broker (see tests/test_mqtt_telemetry.py, which skips by default).
"""
import json
import re

_SANITIZE = re.compile(r"[^A-Za-z0-9_.-]+")


def _segment(value):
    return _SANITIZE.sub("_", str(value)) if value not in (None, "") else "_"


class MqttTelemetryPublisher:
    def __init__(self, host="127.0.0.1", port=1883, topic_prefix="openlogitwin",
                 client_id="openlogitwin-telemetry", timeout=5.0):
        self.host = host
        self.port = port
        self.topic_prefix = topic_prefix.rstrip("/")
        self.client_id = client_id
        self.timeout = timeout
        self._client = None

    def topic_for(self, event) -> str:
        return f"{self.topic_prefix}/{_segment(event.get('scenario'))}/{_segment(event.get('event_type'))}"

    @staticmethod
    def payload_for(event) -> str:
        return json.dumps(event, sort_keys=True)

    def connect(self) -> "MqttTelemetryPublisher":
        import paho.mqtt.client as mqtt  # lazy: optional dependency
        try:  # paho-mqtt >= 2.0 requires a callback API version
            self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=self.client_id)
        except (AttributeError, TypeError):
            self._client = mqtt.Client(client_id=self.client_id)  # paho-mqtt < 2.0
        self._client.connect(self.host, self.port, keepalive=int(self.timeout) + 30)
        self._client.loop_start()
        return self

    def publish(self, event) -> None:
        if self._client is None:
            raise RuntimeError("MqttTelemetryPublisher is not connected")
        self._client.publish(self.topic_for(event), self.payload_for(event), qos=0)

    def close(self) -> None:
        if self._client is not None:
            try:
                self._client.loop_stop()
                self._client.disconnect()
            finally:
                self._client = None

    def as_sink(self):
        """Return a callable for TelemetryLogger(sink=...)."""
        return self.publish
