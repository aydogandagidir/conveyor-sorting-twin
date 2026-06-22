# Deployment Guide (Phase 3a)

OpenLogiTwin runs two ways: **local Python** (zero dependencies) or **Docker Compose**
(soft-PLC + optional FUXA HMI / Node-RED).

## Profiles
| Profile | Services | Use |
|---------|----------|-----|
| `minimal` | soft-PLC | Modbus TCP connectivity endpoint |
| `standard` | soft-PLC | + file-based telemetry (no extra container) |
| `full` | soft-PLC + FUXA | HMI demo |
| `integration` | Node-RED | optional flow integration |

```bash
cp deployment/.env.example deployment/.env      # adjust ports / cell
docker compose -f deployment/docker-compose.yml --profile full up --build
```
Validate the compose file without starting anything:
```bash
docker compose -f deployment/docker-compose.yml --profile full config
```

## Selecting the cell
The soft-PLC image is configured by env vars (see `deployment/.env.example`):
- `OLTWIN_REGISTRY` — `conveyor_sorting_cell` (Phase 0) or `sorting_cell_mvp` (Phase 1 HMI cell)
- `OLTWIN_CONTROL` — `control_logic` / `control_logic_mvp` / `control_logic_advanced`
- `MODBUS_PORT` — host port mapped to the slave (default 15502)

For a FUXA HMI demo of the MVP cell:
```bash
OLTWIN_REGISTRY=sorting_cell_mvp OLTWIN_CONTROL=control_logic_mvp \
  docker compose -f deployment/docker-compose.yml --profile full up --build
```

## Local (no Docker)
```bash
python scripts/run_soft_plc.py        # 127.0.0.1:15502 (Ctrl+C to stop)
# env overrides work the same: OLTWIN_REGISTRY, OLTWIN_CONTROL, OLTWIN_HOST, OLTWIN_PORT
```

## Networking / firewall
- The slave binds `0.0.0.0:15502` in a container, `127.0.0.1:15502` locally.
- **Windows**: first run may prompt Windows Defender Firewall — allow `python.exe`
  (or Docker) inbound on TCP 15502 for the local network only.
- Keep the slave on a trusted/segmented network: this Modbus subset has **no auth**
  (standard for Modbus). Do not expose 15502 to the public internet.

## Health check
A TCP connect + a Read Coils request is a sufficient liveness probe:
```bash
python -c "import socket,struct; s=socket.create_connection(('127.0.0.1',15502),3); \
s.sendall(struct.pack('>HHHBBHH',1,0,6,1,1,0,1)); print('alive' if s.recv(16) else 'down')"
```

## Optional dependencies
- `pytest` — to run `pytest tests/` (the stdlib `scripts/run_tests.py` needs nothing).
- `pymodbus` — to exercise the pymodbus adapter (`tests/test_pymodbus_adapter.py`); skipped if absent.
- `jsonschema` — only if you prefer formal schema validation over the built-in validator.

## Telemetry / exports
Scripts write to `telemetry/exports/` by default; override with `--export-dir=DIR`
(e.g. for CI or a container volume). Exports are gitignored.

## Known limitations
- soft-PLC is a STUB for OpenPLC Runtime v3 (ADR-0002). For real PLC behaviour, point a
  Modbus master at an OpenPLC slave running the equivalent ST program (`plc/examples/`).
- No TLS/auth on the Modbus endpoint (protocol standard). Network-segment it.
