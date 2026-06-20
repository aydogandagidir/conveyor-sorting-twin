# ADR-0006 — OPC UA adapter (second protocol)

- Status: Accepted
- Date: 2026-06-20
- Phase: 2 (protocol extensibility)

## Context
The stack roadmap is Modbus TCP first, **OPC UA second**, MQTT third (ADR-0002). Modbus is
done (in-repo + a verified pymodbus adapter). The gateway is backend-agnostic, so adding OPC UA
should require only a new client adapter — proving the abstraction holds across very different
protocols.

## Decision
Implement a **real OPC UA adapter** on top of `asyncua` (sync API), replacing the OPC UA stub.
- `protocol-gateway/adapters/opcua_adapter.py`: `OpcUaClient` implements the same 6-method
  client interface (`read_coils`/.../`write_register`). Tag coordinates `(table, address)` map to
  OPC UA string NodeIds `"{table}_{address}"` under one namespace, so the Modbus-shaped interface
  maps cleanly onto OPC UA nodes. A `build_opcua_server()` helper exposes the four I/O tables as
  writable nodes (test oracle / OPC-UA-facing I/O image).
- `protocol_factory` `kind="opcua"` now returns the real adapter.
- `asyncua` is **optional** (`pip install asyncua`), imported lazily — importing the module or the
  factory never requires it. `tests/test_opcua_adapter.py` runs a real server+client round-trip
  (and a `TagGateway` over OPC UA) when asyncua is present, and **skips** otherwise, so the
  zero-dependency suite stays green.

## Rationale
- Closes the second protocol priority with a genuine implementation (not a stub), while keeping
  the core zero-dependency.
- The same `TagGateway` / registry / control logic run unchanged over Modbus, in-process,
  pymodbus, and OPC UA — strong evidence the gateway abstraction is right.

## Consequences
- Verified against asyncua 2.0 (sync API); `read_register` values are exchanged as `UInt16`.
- A `server_to_store` / `store_to_server` bridge lets a full sorting cycle run **end-to-end over
  OPC UA** (the gateway over the wire, the soft-PLC scanning the mirrored process image) — see
  `tests/test_opcua_full_loop.py`, not just a single-node round-trip.
- The unsecured OPC UA endpoint is for local simulation/training only (no auth/encryption) — same
  caution as the Modbus endpoint (see `SECURITY.md`).
- MQTT remains a stub (`adapters/mqtt_stub.py`) — third priority, pub/sub semantics to reconcile.
  *(Superseded: MQTT telemetry is now real — see ADR-0007.)*

## Alternatives considered
- **Keep the OPC UA stub**: rejected — OPC UA is the next roadmap protocol and `asyncua` makes a
  real, verifiable adapter cheap.
- **Map by tag name instead of (table, address)**: rejected for now — the gateway speaks the
  Modbus-shaped interface; `(table, address)` keeps one mapping rule across all adapters.
