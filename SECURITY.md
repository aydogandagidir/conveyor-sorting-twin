# Security Policy

## Reporting a vulnerability
Please report security issues **privately** via GitHub's
[**Report a vulnerability**](https://github.com/aydogandagidir/conveyor-sorting-twin/security/advisories/new)
(Security Advisories) on this repository — not a public issue. We aim to acknowledge within a
few days.

## Important security notes
- The Modbus TCP endpoint has **no authentication or encryption** — this is standard for Modbus.
  Do **not** expose it to untrusted networks; keep it on a segmented/trusted LAN. See
  [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).
- OpenLogiTwin is a **simulator / training tool**, not safety-rated industrial control software.
  Do not use it to control real machinery.

## Supported versions
The latest `main` is supported. The project is pre-1.0; APIs and tags may change.
