# Sample OpenPLC programs (Phase 3b)

Structured Text (IEC 61131-3) ports of the soft-PLC control logic, for use with
**OpenPLC Runtime v4**. They let you replace the Python soft-PLC stub (ADR-0002) with
a real PLC while keeping the gateway, tag registry and scenarios unchanged.

- `01_basic_conveyor_latch.st` — start/stop/E-stop motor latch (teaching baseline).
- `02_sorting_cell_mvp.st` — full cell: routing, counting, jam timer (ports `control_logic_mvp.py`).

> STATUS: `02_sorting_cell_mvp.st` **compiles and runs on OpenPLC Runtime v3** — verified
> 2026-06-20 (loaded, compiled with 0 errors, PLC *Running*, gateway smoke test passed). It is
> also structure-checked by `tests/test_st_examples.py`. `01_basic_conveyor_latch.st` is
> structure-checked but not yet runtime-verified.

## Load into OpenPLC Runtime
1. Open the OpenPLC web editor → **Programs** → upload the `.st` file.
2. **Compile**, then **Start PLC**. (`02_sorting_cell_mvp.st` compiles as-is — see the MatIEC notes.)
3. The Modbus TCP slave is served on port 502 — point a master at it (the gateway, FUXA, or
   `scenario_runner` with a pymodbus client).

**Two MatIEC requirements** (learned by running this on OpenPLC v3 — both already applied to
`02_sorting_cell_mvp.st`):
- **Separate VAR blocks.** Located variables (`AT %…`) and internal/FB variables must live in
  *different* `VAR … END_VAR` blocks; mixing them in one block fails with
  `invalid located variable declaration`.
- **A `CONFIGURATION`/`RESOURCE`/`TASK`** block is required to compile a stand-alone file
  (appended to the example).

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

> **OpenPLC's Modbus map mirrors the soft-PLC's.** OpenPLC fixes `%QX→coils`, `%IX→discrete
> inputs`, `%IW→input regs`, `%QW→holding regs`. So against OpenPLC a master **reads outputs from
> coils** and **reads inputs from discrete inputs** — the opposite tables from the in-repo
> soft-PLC. The smoke test below reads both and just checks the slave answers.

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
It skips cleanly when `OPENPLC_HOST` is unset (so CI stays green). **Verified 2026-06-20** against
OpenPLC Runtime v3 (Docker, host port 1502): with the compiled program *Running*, the gateway
connected to the slave and read the live I/O image (motor/diverter/jam coils, sensor discrete
inputs, counter registers) — `1 passed`. Full ST-vs-soft-PLC behavioural equivalence (driving the
scenarios and comparing counters) remains a guided **manual** procedure, because OpenPLC's input
image (`%IX` / discrete inputs) is not writable over standard Modbus.
