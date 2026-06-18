# protocol-gateway

The protocol layer: a standards-compliant **Modbus TCP** subset, the **tag registry**,
and a backend-agnostic **gateway** that maps named tags to Modbus addresses.

- `modbus_tcp.py` — Modbus TCP server/client + `ModbusDataStore` + `LocalStoreClient`.
- `tag_registry.py` — `Tag` / `TagRegistry`, structural validation, master/slave semantics.
- `gateway.py` — `TagGateway` (tag ↔ Modbus), works with TCP or in-process clients.
- `config/` — tag registry instances; `schema/` — JSON Schema for tag registries.

## Modbus function code coverage
Real MBAP framing; a deliberate **subset** for this cell (swappable for pymodbus /
OpenPLC — see `adr/0002`, `adr/0003`).

| FC | Name | Role |
|----|------|------|
| 0x01 | Read Coils | master reads sensor/setpoint coils |
| 0x02 | Read Discrete Inputs | master reads actuator/alarm bits |
| 0x03 | Read Holding Registers | master reads setpoints (e.g. destination) |
| 0x04 | Read Input Registers | master reads counters/metrics |
| 0x05 | Write Single Coil | master writes a sensor/button/E-stop |
| 0x06 | Write Single Register | master writes a setpoint |
| 0x0F | Write Multiple Coils | batch coil write |
| 0x10 | Write Multiple Registers | batch register write |

Unsupported function codes return a proper Modbus exception response
(`fc | 0x80` + `ILLEGAL_FUNCTION`). Other exceptions: `ILLEGAL_DATA_ADDRESS`
(out-of-range), `ILLEGAL_DATA_VALUE` (bad count/value).

## Master/slave tag semantics
The gateway is the master, the soft-PLC the slave. The registry enforces:
- `sim_to_plc` (sensors, buttons, setpoints) → master-writable `coil` / `holding_register`.
- `plc_to_sim` (actuators, alarms, counters) → master-readable `discrete_input` / `input_register`.

## Tag I/O conditioning: `invert` (NC fail-safe)
A bool tag may set `"invert": true`. The soft-PLC then presents the logical value to
the control program — used for a **normally-closed, de-energize-to-trip E-stop**
(raw wire true=healthy → logical engaged=false). See `adr/0004` and
`tests/test_estop_failsafe.py`.

## Extensibility
`TagGateway` needs only a client implementing 6 methods (`read_coils`,
`read_discrete_inputs`, `read_holding_registers`, `read_input_registers`,
`write_coil`, `write_register`). A `pymodbus` adapter or an OPC UA/MQTT bridge plugs
in without touching the gateway, registry, scene, or control logic (Phase 2).
