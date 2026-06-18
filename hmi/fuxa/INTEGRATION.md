# FUXA Integration Guide (Phase 2)

Connect a FUXA HMI to the OpenLogiTwin sorting cell over Modbus TCP.

## 1. Start the PLC endpoint (Modbus slave)
```bash
python scripts/run_soft_plc.py            # soft-PLC stub, 127.0.0.1:15502
```
(Phase 0/1 cells; the same applies to a real OpenPLC slave later.)

> Tip: drive the cell from scenarios while watching the HMI:
> `python scripts/scenario_manager.py run-all`

## 2. Bring up FUXA
```bash
docker compose --profile hmi up           # deployment/docker-compose.yml
```
FUXA UI: http://localhost:1881

## 3. Add the Modbus device + tags
The device tag list is generated from the registry (never hand-edited):
```bash
python scripts/generate_hmi_tag_list.py   # -> hmi/fuxa/tag_list_sorting_cell_mvp.csv
```
In FUXA → **Devices** → add a **Modbus TCP** device:
- Address `127.0.0.1`, port `15502`, slave/unit id `1`.
- Add tags using `tag_list_sorting_cell_mvp.csv`. The `modicon_ref` column gives the
  classic reference (coils `0xxxx`, discrete inputs `1xxxx`, input registers `3xxxx`,
  holding registers `4xxxx`); `address_0based` is the raw offset if FUXA uses 0-based.

## 4. Suggested widget bindings
| Widget | Tag(s) | Modbus |
|--------|--------|--------|
| Start / Stop / Reset buttons | `input.start_pb` / `input.stop_pb` / `input.reset_pb` | coils 2/3/4 (write) |
| E-stop button | `input.estop` | coil 5 (write) |
| Motor lamp | `output.motor_conv_001_run` | discrete input 0 (read) |
| Jam alarm | `alarm.jam_001` | discrete input 2 (read) |
| Chute A / B counters | `counter.sorted_chute_a` / `_b` | input registers 0/1 (read) |
| Destination setpoint | `data.parcel_destination` | holding register 0 (write) |

## Status
- ✅ Device tag list (auto-generated, drift-guarded by `tests/test_hmi_tag_list.py`).
- ✅ Integration steps (this file) + `docker-compose` `hmi` profile.
- 🟡 Generated FUXA project `hmi/fuxa/openlogitwin_project.json` — a ModbusTCP device + the
  12 tags built from the registry following FUXA's data model (`scripts/generate_fuxa_project.py`,
  structure-tested). **Best-effort: import into FUXA to confirm**; adjust type/access strings
  or the project envelope to your FUXA version if needed.
- ⬜ SVG mimic screens — drawn in the FUXA editor and bound to the imported tags.
