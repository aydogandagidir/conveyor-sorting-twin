# Security Policy

## Reporting a vulnerability
Please report security issues **privately** via GitHub's
[**Report a vulnerability**](https://github.com/aydogandagidir/conveyor-sorting-twin/security/advisories/new)
(Security Advisories) on this repository — not a public issue. We aim to acknowledge within a
few days.

## Important security notes
- The Modbus TCP endpoint has **no authentication or encryption** — this is standard for Modbus.
  Do **not** expose it to untrusted networks; keep it on a segmented/trusted LAN. See
  [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md). The OPC UA and MQTT endpoints carry the same caveat.
- The **live HMI WebSocket server** (`scripts/hmi_server.py`, default `ws://127.0.0.1:8765`) likewise
  has **no authentication or encryption**, and it accepts control commands (start / stop / reset /
  E-stop / inject-jam) that drive the soft-PLC. Keep it on `127.0.0.1` or a trusted LAN; do **not**
  bind it to a public interface (`HMI_HOST=0.0.0.0`) on an untrusted network. The static GitHub
  Pages HMI is replay-only and runs no server.
- OpenLogiTwin is a **simulator / training tool**, not safety-rated industrial control software.
  Do not use it to control real machinery.

## Supported versions
The latest `main` is supported. The project is pre-1.0; APIs and tags may change.
