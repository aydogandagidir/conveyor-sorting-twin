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

> **Two gotchas on FUXA 1.3+ (verified against `frangoteam/fuxa` v1.3.3, 2026-06-20):**
> 1. **Install the Modbus device plugin.** Comm drivers are dynamic plugins; an uninstalled one
>    logs `try to create … but plugin is missing!`. Install **Modbus** (`modbus-serial`) from
>    *Settings → Device Plugins*. Headless: `docker exec <fuxa> sh -c "cd /usr/src/app/FUXA/server && npm i modbus-serial"`, then restart.
> 2. **Put the port *inside* the address.** FUXA's TCP driver ignores the separate port field and
>    parses `host:port` from the address (defaulting to 502). Use address `127.0.0.1:15502`
>    (or `host.docker.internal:15502` when FUXA runs in a container reaching a host PLC).

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
- ✅ Generated FUXA project `hmi/fuxa/openlogitwin_project.json` (ModbusTCP device + 12 registry
  tags). **Verified 2026-06-20**: imported into FUXA v1.3.3 via its API, the device connects and
  polls the soft-PLC, and live values propagate (e.g. `data.parcel_destination` 1→2→7 tracked).
  FUXA's own Modbus lib (`modbus-serial`) reads all four function codes from the twin cleanly.
- ⬜ SVG mimic screens — drawn in the FUXA editor and bound to the imported tags (cosmetic; the
  data path above is independent of the drawing).
