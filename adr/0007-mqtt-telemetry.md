# ADR-0007 — MQTT telemetry (third protocol)

- Status: Accepted
- Date: 2026-06-20
- Phase: 2/3 (protocol extensibility / telemetry)

## Context
The stack roadmap is Modbus first, OPC UA second, **MQTT third**, framed specifically as
"MQTT telemetry" (ADR-0002, master prompt). Modbus and OPC UA are request/response gateway
transports. MQTT is **publish/subscribe** — it does not fit the synchronous gateway client
interface (a `read_coils` over pub/sub is a poor fit).

## Decision
Implement MQTT as a **telemetry sink**, not a gateway transport.
- `telemetry/mqtt_publisher.py`: `MqttTelemetryPublisher` publishes each telemetry event to a
  topic `"{prefix}/{scenario}/{event_type}"` with a JSON payload. Topic/payload formatting is
  pure; the broker connection uses `paho-mqtt` (lazy import, optional dependency).
- `TelemetryLogger` gains an optional `sink=` callback, invoked per event (default `None` →
  unchanged behaviour). Wire MQTT with `TelemetryLogger(db, sink=publisher.as_sink())`. A failing
  sink is caught and logged — it never crashes the run.
- The gateway-transport factory keeps an `mqtt` **stub** that raises `NotImplementedError` with a
  message pointing here (MQTT is telemetry, not a gateway client).

## Rationale
- Honors the protocol roadmap with the *right* MQTT shape (telemetry streaming), not a forced
  request/response mapping.
- The sink hook is a one-line, non-breaking extension; formatting is unit-tested without a broker,
  and a real publish/subscribe round-trip is verified when a broker is available.

## Verification
- `tests/test_mqtt_telemetry.py`: topic/payload formatting + the sink hook + sink-failure
  resilience run with **no dependencies**; a real round-trip runs only when `paho-mqtt` is
  installed and `MQTT_HOST` is set (skip-by-default).
- Verified end-to-end against a real broker (paho-mqtt + amqtt): an event published by
  `MqttTelemetryPublisher` was received on `openlogitwin/<scenario>/<event_type>` with the JSON payload.

## Consequences
- `paho-mqtt` is an optional dev dependency; the zero-dependency core/CI is unaffected.
- No auth/TLS on the example broker usage — telemetry may contain operational data; secure the
  broker on real deployments (see `SECURITY.md`).

## Alternatives considered
- **MQTT as a gateway transport**: rejected — pub/sub ≠ request/response; telemetry is the
  documented use.
- **Live sink vs post-hoc DB publish**: chose the live `sink` hook (stream as events occur);
  a batch publisher over the SQLite rows can be layered on later if needed.
