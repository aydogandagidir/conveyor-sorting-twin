# Phase 0 — Run & Verify Guide

## Requirements
- Python 3.9+ (developed/verified on 3.13). **No third-party packages required.**
- No Docker needed for Phase 0. (`deployment/docker-compose.yml` is for later HMI phases.)

## Verify the Gate-1 loop
```bash
python tests/verify_phase0.py
```
Expected: a printed checklist ending with `RESULT: PASS - 19/19 checks passed`
and exit code 0. Telemetry is exported to:
- `telemetry/exports/phase0_verify.csv`
- `telemetry/exports/phase0_verify.json`

Windows wrapper: `scripts/verify_phase_0.ps1` · POSIX wrapper: `scripts/verify_phase_0.sh`.

## Run the human-readable demo
```bash
python scripts/run_demo.py
```
Streams parcels through the cell and prints routing decisions, then writes
`telemetry/exports/demo.json`.

## Run the soft-PLC as a standalone Modbus slave
```bash
python scripts/run_soft_plc.py          # listens on 127.0.0.1:15502
OLTWIN_PORT=15600 python scripts/run_soft_plc.py
```
Any Modbus TCP master can then connect (the gateway, a SCADA, or a poll tool).
This is the soft-PLC stand-in (ADR-0002) — a deterministic test oracle; a real OpenPLC Runtime v3
was verified equivalent in 0.5.0 (see [`plc/examples/README.md`](../plc/examples/README.md)).

## Tag map (quick reference)
| Tag                   | Dir         | Modbus table     | Addr |
|-----------------------|-------------|------------------|------|
| `sensor.infeed`       | sim→plc     | coil             | 0    |
| `sensor.preDivert`    | sim→plc     | coil             | 1    |
| `sensor.chute1`       | sim→plc     | coil             | 2    |
| `sensor.chute2`       | sim→plc     | coil             | 3    |
| `estop`               | sim→plc     | coil             | 4    |
| `barcode.destination` | sim→plc     | holding_register | 0    |
| `motor.conveyor`      | plc→sim     | discrete_input   | 0    |
| `diverter.armA`       | plc→sim     | discrete_input   | 1    |
| `diverter.armB`       | plc→sim     | discrete_input   | 2    |
| `fault.jam`           | plc→sim     | discrete_input   | 3    |
| `indicator.running`   | plc→sim     | discrete_input   | 4    |
| `throughput.count`    | plc→sim     | input_register   | 0    |

## Troubleshooting
- **Port already in use**: the verifier uses an OS-assigned free port (`port=0`).
  Only `run_soft_plc.py` binds a fixed port; override with `OLTWIN_PORT`.
- **Firewall prompt on Windows**: the server binds `127.0.0.1` (loopback) only;
  allow local access if prompted.

## What works / what's a stub (be precise)
- **Works (real):** Modbus TCP framing, tag mapping, control scan, telemetry export.
- **Stub (clearly marked):** `plc/soft_plc.py` (→ OpenPLC) and
  `simulation/cell_sim.py` (→ Godot). Each carries TODO replacement criteria.
