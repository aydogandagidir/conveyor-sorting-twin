# ADR-0009 — Live HMI transport: hand-rolled WebSocket, stdlib only

Status: Accepted (2026-06-22)

## Context
The web HMI (V0–V2) replayed deterministic traces exported by `scripts/export_trace.py` — a
zero-install, GitHub-Pages-friendly view with no server. V3 adds a **live** mode: stream the
running twin (soft-PLC + `scene_model.py`) to the browser in real time and let the operator drive
it (start / stop / reset / E-stop / inject-jam). That needs a bidirectional, low-latency,
browser-native transport. The repo's existing protocols don't fit the browser: a raw browser page
cannot speak Modbus/TCP or OPC UA, and MQTT-over-WebSocket would pull in a broker + client library.

Constraints from the project ethos: **stdlib-only core, no new runtime dependencies** (ADR-0002),
and the live server must reuse the verified twin (the same `SoftPlc` + control logic the suite
checks), not a parallel mock.

## Decision
- **Hand-roll a minimal WebSocket (RFC 6455) server in `scripts/hmi_server.py`** — SHA-1 + base64
  `Sec-WebSocket-Accept` handshake and text framing (mask/unmask, ≥126-byte length, continuation
  reassembly, PING→PONG, close) — pure stdlib, the same zero-dependency stance as the in-repo
  Modbus server. WebSocket is the only transport a stock browser page speaks bidirectionally
  without a plugin or library.
- **Run the real twin in real time.** `TwinEngine` wraps the same `SoftPlc(control_logic_mvp)` +
  `SceneModel` the suite verifies, auto-feeds parcels, and broadcasts one JSON frame per tick (the
  same shape as an exported trace frame, plus an `estop` flag). HMI commands are JSON
  `{"cmd": ...}` messages that drive the actual control logic — the buttons are live, not faked.
- **Keep replay the default.** The static GitHub Pages deployment stays replay-only (no server);
  live mode is opt-in for local/LAN (`ws://127.0.0.1:8765`, `HMI_HOST`/`HMI_PORT`).

## Rationale
- **No black boxes, no deps.** A ~120-line RFC 6455 subset is in the same teaching spirit as the
  in-repo Modbus stack, and keeps `dependencies = []`. A library (`websockets`, `aiohttp`) would
  add the version/setup risk ADR-0002 deliberately avoids.
- **One source of truth.** Reusing `SoftPlc` + `SceneModel` means the live console and the test
  suite exercise the *same* plant — the live view can't silently diverge from what's verified.
- **Graceful degradation.** Pages stays a zero-install demo; the live server is additive and local.

## Consequences
- `tests/test_hmi_server.py` covers the handshake/framing end-to-end and that commands
  (start/stop/reset/estop/jam) drive the soft-PLC, plus jam-latch + reset recovery and the `estop`
  frame flag — all stdlib, runs in CI.
- The server has **no authentication or encryption** (like the Modbus/OPC UA endpoints). It accepts
  control commands, so it must stay on `127.0.0.1` / a trusted LAN — documented in `SECURITY.md`.
- The framing subset is intentionally limited: one broadcast text stream + small inbound command
  frames. Not addressed (no consumer): permessage-deflate, binary frames, TLS (`wss://`), and
  per-client backpressure beyond reaping a dead socket. Add when a real deployment needs them.

## Alternatives considered
- **A WebSocket library (`websockets`/`aiohttp`)**: rejected — adds a runtime dependency and async
  framework for ~120 lines of well-understood protocol; against the stdlib-only core.
- **Server-Sent Events (SSE) + a POST endpoint for commands**: viable and simpler one-way, but
  needs a second channel for commands and an HTTP server; WebSocket gives one bidirectional socket.
- **Long-polling / a REST tick endpoint**: rejected — higher latency and overhead for a real-time
  mimic; poor fit for ~10 Hz frames.
- **MQTT-over-WebSocket**: rejected — pulls in a broker + JS client; heavier than the need.
