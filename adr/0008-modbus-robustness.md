# ADR-0008 — Modbus client robustness: auto-reconnect + multi-word register types

Status: Accepted (2026-06-20)

## Context
The in-repo `ModbusTCPClient` (ADR-0002) was a minimal, single-shot master: a dropped socket
surfaced as a raw `OSError`/`ConnectionError` to the caller, and the tag model only spoke `bool`
and `uint16`. Two gaps for longer-running / richer use (Track A, A8):
1. A transient TCP drop (PLC restart, network blip) killed an otherwise-fine session.
2. Real cells carry 32-bit values (running totals, rates) that don't fit one 16-bit register.

## Decision
- **Auto-reconnect once on transport failure.** `_request` catches `OSError`/`ConnectionError`,
  reconnects, and retries the request exactly once. A Modbus **exception response** (a valid reply)
  is *not* caught — it still raises `ModbusError`. The retry is bounded (one attempt) so a truly
  down peer fails fast rather than looping.
- **Multi-word register types `uint32` / `float32`.** Added to `VALID_TYPES`; `Tag.word_count`
  reports the register span (2 for these, 1 otherwise). A big-endian word-order codec
  (`encode_registers` / `decode_registers`) lives in `modbus_tcp.py`, and `TagGateway`
  read/writes `word_count` consecutive registers — so a typed tag round-trips transparently.

## Rationale
- One reconnect+retry covers the common transient case without masking a persistent outage or
  risking an unbounded loop; the per-request lock is released before retry (no deadlock).
- Big-endian (high word first) is the prevailing Modbus convention and matches typical PLC/SCADA
  defaults; keeping the codec in `modbus_tcp.py` keeps the encoding next to the framing.
- Behaviour is additive: `bool`/`uint16` tags are byte-for-byte unchanged (`word_count == 1`).

## Consequences
- `gateway.py` now imports the codec from `modbus_tcp.py` (same package, stdlib only).
- `tests/test_modbus_robustness.py` covers reconnect-after-drop and a `uint32`/`float32` round-trip
  over the real server.
- Not yet addressed (low priority, no consumer): little-endian / word-swap variants, atomic
  multi-register writes (FC16 from the client — today two FC06 writes), and address-overlap
  validation for multi-word tags. Add when a registry actually needs them.

## Alternatives considered
- **Infinite reconnect loop / backoff**: rejected for the in-repo client — hides outages and
  complicates a teaching implementation. One retry is enough; callers can wrap for more.
- **A separate codec module**: rejected — the encoding belongs with the Modbus framing it serves.
