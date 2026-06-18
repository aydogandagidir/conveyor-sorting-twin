# Sample OpenPLC programs (Phase 3b)

Structured Text (IEC 61131-3) ports of the soft-PLC control logic, for use with
**OpenPLC Runtime v4**. They let you replace the Python soft-PLC stub (ADR-0002) with
a real PLC while keeping the gateway, tag registry and scenarios unchanged.

- `01_basic_conveyor_latch.st` — start/stop/E-stop motor latch (teaching baseline).
- `02_sorting_cell_mvp.st` — full cell: routing, counting, jam timer (ports `control_logic_mvp.py`).

> STATUS: provided as-is. ST is validated structurally by `tests/test_st_examples.py`, but
> **must be compiled in the OpenPLC editor** before deployment — there is no ST compiler in
> this repo.

## Load into OpenPLC Runtime v4
1. Open the OpenPLC web editor → **Programs** → upload the `.st` file.
2. Compile. Fix any editor-flagged issues (toolchains differ slightly on edge syntax).
3. **Settings → Slave Devices / Modbus**: enable the Modbus TCP server (port 502 or your choice).
4. Run. Point a master at it (the gateway, FUXA, or `scenario_runner` with a pymodbus client).

## Tag → OpenPLC address mapping (`02_sorting_cell_mvp.st`)
| Tag (registry) | Direction | Modbus (gateway) | OpenPLC address |
|----------------|-----------|------------------|-----------------|
| `sensor.pe_001` | sim→plc | coil 0 | `%IX0.0` |
| `sensor.pe_002` | sim→plc | coil 1 | `%IX0.1` |
| `input.start_pb` | sim→plc | coil 2 | `%IX0.2` |
| `input.stop_pb` | sim→plc | coil 3 | `%IX0.3` |
| `input.reset_pb` | sim→plc | coil 4 | `%IX0.4` |
| `input.estop` | sim→plc | coil 5 | `%IX0.5` |
| `data.parcel_destination` | sim→plc | holding reg 0 | `%IW0` |
| `output.motor_conv_001_run` | plc→sim | discrete input 0 | `%QX0.0` |
| `output.diverter_dv_001_extend` | plc→sim | discrete input 1 | `%QX0.1` |
| `alarm.jam_001` | plc→sim | discrete input 2 | `%QX0.2` |
| `counter.sorted_chute_a` | plc→sim | input reg 0 | `%QW0` |
| `counter.sorted_chute_b` | plc→sim | input reg 1 | `%QW1` |

(Holding registers the master writes are PLC **inputs** `%IW`; input registers the master
reads are PLC **outputs** `%QW`.)

## E-stop inversion (ADR-0004)
The ST computes `estop_engaged := NOT estop_in` for a **normally-closed, de-energize-to-trip**
button: a healthy circuit reads TRUE, a pressed/broken circuit reads FALSE → engaged. If your
hardware uses a normally-open (active-true) button instead, change it to
`estop_engaged := estop_in`. The Python soft-PLC achieves the same via the tag `invert` flag.

## Verify against a live OpenPLC
A **skip-by-default connectivity smoke test** is provided — it confirms the gateway can reach
and exchange Modbus reads with a running OpenPLC slave:
```bash
OPENPLC_HOST=127.0.0.1 OPENPLC_PORT=502 python tests/test_openplc_integration.py
```
It skips cleanly when `OPENPLC_HOST` is unset (so CI stays green). Full ST-vs-soft-PLC
behavioural equivalence (driving the shipped scenarios and comparing counters) is a guided
**manual** procedure, because it depends on your OpenPLC I/O→Modbus address mapping.
