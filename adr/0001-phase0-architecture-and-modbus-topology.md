# ADR-0001 — Phase 0 architecture and Modbus topology

- Status: Accepted
- Date: 2026-06-17
- Phase: 0 (PoC Connectivity)

## Context
Phase 0 must prove the Engineering Gate 1 loop (sensor → tag registry → gateway
→ PLC logic → actuator → simulation → telemetry) with the smallest credible
implementation, while staying faithful to the target stack (Modbus TCP first,
OpenPLC, SQLite telemetry).

## Decision
1. **Single conveyor sorting cell** with 12 tags; no generic factory model.
2. **Gateway = Modbus master, PLC = Modbus slave.** The soft-PLC owns the I/O
   process image (`ModbusDataStore`); the gateway reads/writes it over TCP.
3. **Tag tables follow Modbus master semantics:**
   - `sim_to_plc` (sensors, setpoints) → master-writable `coil` / `holding_register`.
   - `plc_to_sim` (actuators, metrics) → master-readable `discrete_input` / `input_register`.
   The registry validator enforces this, preventing illegal mappings.
4. **Control logic is pure and transport-agnostic** (`plc/control_logic.py`), so
   the identical scan runs in the soft-PLC and in the local fallback.
5. **Backend-agnostic gateway:** one `TagGateway` works with a real TCP client or
   an in-process `LocalStoreClient`.
6. **Telemetry is SQLite-first** with CSV/JSON export.

## Rationale
- Mirrors a real SCADA-master ↔ OpenPLC-slave topology, so the design survives
  the later stub→OpenPLC swap without re-architecting tag mapping.
- Pure control logic is unit-testable and reusable across transports.
- Master/table consistency caught at registry-load time avoids a whole class of
  wiring bugs.

## Consequences
- Actuator outputs live in Modbus *read-only* tables (from the master's view).
  This is correct and standard but can surprise newcomers — documented in
  `docs/ARCHITECTURE.md`.
- Adding a tag = one registry entry + (if new) control-logic handling.

## Alternatives considered
- **Gateway as slave / sim as master:** rejected; OpenPLC is naturally the slave
  in this product, and matching that now avoids rework.
- **Generic multi-cell model:** rejected as over-scope for Phase 0 (Rule: build
  narrow, not a warehouse engine).
