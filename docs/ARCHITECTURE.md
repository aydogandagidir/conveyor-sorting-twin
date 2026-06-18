# OpenLogiTwin — Architecture (Phase 0)

## Scope
Phase 0 proves connectivity for a single **conveyor sorting cell**. It is a
narrow, demo-ready intralogistics PoC — not a generic factory simulator.

## Component map (Phase 0)

```
+------------------------+        named tags         +-------------------------+
|  simulation/cell_sim   |  ---------------------->  |  protocol-gateway       |
|  (Godot STUB)          |   write sensor tags       |  gateway.TagGateway     |
|                        |  <----------------------  |  (Modbus master)        |
+------------------------+   read actuator tags      +-----------+-------------+
            ^                                                     |
            | telemetry events                                   | Modbus TCP
            v                                                     v  (real MBAP)
+------------------------+                            +-------------------------+
|  telemetry             |                            |  plc/soft_plc (STUB)    |
|  SQLite + CSV/JSON      |                            |  Modbus slave + scan    |
+------------------------+                            |  plc/control_logic      |
                                                      +-------------------------+
```

The gateway is **backend-agnostic**: the same `TagGateway` runs against either
- `ModbusTCPClient` — the real Modbus TCP proof path, or
- `LocalStoreClient` — the in-process local control fallback (no sockets).

## Data flow (Engineering Gate 1)
1. `cell_sim` writes a sensor tag (e.g. `sensor.preDivert = true`) via the gateway.
2. The gateway maps the tag → Modbus coil and writes it (TCP master → slave).
3. The soft-PLC scan reads its inputs, runs `control_logic.scan()`.
4. The scan writes outputs (`motor.conveyor`, `diverter.armA/armB`, `throughput.count`)
   into the data store (discrete inputs / input registers).
5. The gateway reads those output tags back (master read).
6. `telemetry_logger` records the transition to SQLite; exportable to CSV/JSON.

## Modbus topology & tag tables
The soft-PLC owns the I/O process image (`ModbusDataStore`). The gateway is the
master. Modbus master semantics drive the table assignment:

| Direction      | Who writes | Modbus table(s)                     | Example tags                         |
|----------------|------------|-------------------------------------|--------------------------------------|
| `sim_to_plc`   | gateway    | `coil`, `holding_register`          | `sensor.*`, `estop`, `barcode.destination` |
| `plc_to_sim`   | soft-PLC   | `discrete_input`, `input_register`  | `motor.conveyor`, `diverter.*`, `throughput.count` |

`tag_registry.validate_registry()` enforces this consistency, so a sensor can
never be mapped to a read-only table (and vice versa). This mirrors how a real
SCADA master talks to OpenPLC, so the topology survives the stub→OpenPLC swap.

## Tag registry
- Instance: `protocol-gateway/config/tags.conveyor_sorting_cell.json` (12 tags).
- Schema:   `protocol-gateway/schema/tag_registry.schema.json` (JSON Schema draft-07).
- Loader:   `protocol-gateway/tag_registry.py` (dependency-free structural validation).

## Control logic (the "PLC program")
`plc/control_logic.py` — pure, transport-agnostic `scan(inputs, state)`:
- E-stop engaged → motor + indicators off (safety override).
- Jam latched → conveyor held stopped (auto-set: Phase 1 TODO).
- Running → motor + indicator on.
- At the divert point: destination 1 → arm A, 2 → arm B, 3 → straight.
- Throughput counts a parcel on the rising edge of `sensor.preDivert`.

## What is intentionally NOT here (Phase 0)
- Godot 3D scene (Phase 1) — `cell_sim.py` is the stand-in.
- Real OpenPLC Runtime (Phase 1) — `soft_plc.py` is the stub.
- HMI/FUXA (Phase 2), OPC UA (2nd), MQTT (3rd).
- Web console, scenario manager, installer.

See `adr/` for the rationale behind each decision.
