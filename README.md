# OpenLogiTwin — Conveyor Sorting Cell Digital Twin

[![CI](https://github.com/aydogandagidir/conveyor-sorting-twin/actions/workflows/verify.yml/badge.svg)](https://github.com/aydogandagidir/conveyor-sorting-twin/actions/workflows/verify.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](pyproject.toml)
[![runtime deps: stdlib only](https://img.shields.io/badge/runtime%20deps-stdlib%20only-success.svg)](#quickstart)
[![live demo report](https://img.shields.io/badge/live-demo%20report-8a2be2.svg)](https://aydogandagidir.github.io/conveyor-sorting-twin/)

A **narrow, demo-ready, technically credible** intralogistics digital twin: virtual parcels
ride a conveyor, photo-eyes detect them, a decoded barcode drives a diverter, **PLC logic**
controls the outputs over **real Modbus TCP**, an HMI/SCADA can monitor it, and telemetry
records throughput and faults.

Not a generic factory simulator, not a Factory I/O clone — a focused, verifiable slice of
warehouse automation you can run, test, and extend.

---

## Why it's interesting
- **A real industrial protocol, from scratch** — a standards-compliant Modbus TCP server/client
  (MBAP framing, function codes 01–06/0F/10, proper exception responses) in pure stdlib. No black boxes.
- **Deterministic by design** — a fixed-step plant + lock-step PLC scan make every scenario
  bit-reproducible; CI asserts identical re-runs.
- **Honest engineering** — stubs are named `stub` with TODO criteria, decisions live in [`adr/`](adr),
  nothing is faked. Optional integrations (pymodbus, OpenPLC, FUXA, Godot) degrade/skip cleanly.
- **Tested & green** — 14 dual-mode test files run by one stdlib command and a
  Python 3.9–3.13 × Ubuntu/Windows CI matrix.

## Architecture
```
virtual sensor event → tag registry → protocol gateway (Modbus TCP)
   → soft-PLC control logic → actuator output → scene reads output
   → telemetry event (SQLite → CSV/JSON)
```
The gateway is backend-agnostic (in-repo Modbus, in-process, or pymodbus); the soft-PLC takes a
swappable control program and is a documented stand-in for **OpenPLC Runtime v4**.
Full design: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) · decisions: [`adr/`](adr).

## Quickstart
```bash
git clone https://github.com/aydogandagidir/conveyor-sorting-twin.git
cd conveyor-sorting-twin

python scripts/run_tests.py                 # full suite → SUITE GREEN (no dependencies)
python scripts/run_full_demo.py             # run all scenarios → telemetry/exports/demo_report.html
python scripts/scenario_manager.py run-all  # scenario suite, checks each expect block
```
The core needs **no third-party packages** (Python 3.9+); `pytest` / `pymodbus` are optional dev extras.

## Status
| Phase | Scope | State |
|-------|-------|-------|
| 0 — PoC Connectivity | real Modbus TCP loop, tag registry, soft-PLC, telemetry | ✅ 19/19 |
| 1 — MVP Scene | deterministic sorting cell: routing, jam, counters | ✅ 14/14 |
| 1.5 — Hardening | CI, pytest, control unit tests, E-stop NC fail-safe, multi-parcel FIFO | ✅ |
| 2 — HMI + Scenario Manager | scenario CLI, fault scenarios, pymodbus adapter, FUXA tag list | 🟡 mimic screens pending |
| 3 — Productization | demo + report, deployment, sample OpenPLC ST, training docs | 🟡 verifiable parts done |

Roadmap: [`docs/ROADMAP.md`](docs/ROADMAP.md) · changelog: [`docs/CHANGELOG.md`](docs/CHANGELOG.md).

## Repository layout
```
.
├── protocol-gateway/   # Modbus TCP (server/client/store), tag registry, gateway, adapters/
│   ├── config/  schema/  adapters/    # registries, JSON schema, pymodbus / OPC-UA / MQTT
├── plc/                # control logic (Phase 0 / MVP / advanced), soft-PLC stub, examples/*.st
├── simulation/         # deterministic scene model, scenario runner, godot-project/
├── telemetry/          # SQLite logger + CSV/JSON export
├── scenarios/          # deterministic scenario JSONs + schema
├── hmi/fuxa/           # FUXA tag list + project generator + integration guide
├── deployment/         # Dockerfile + profiled docker-compose + .env.example
├── tests/              # 14 dual-mode test files (run directly or via pytest)
├── scripts/            # run_tests, run_full_demo, scenario_manager, generators
└── docs/  adr/  sprints/
```

## Run it for real
- **Soft-PLC over Modbus** — `python scripts/run_soft_plc.py`, or `docker compose -f deployment/docker-compose.yml --profile full up --build`.
- **HMI (FUXA)** — [`hmi/fuxa/INTEGRATION.md`](hmi/fuxa/INTEGRATION.md).
- **Real PLC** — load [`plc/examples/*.st`](plc/examples) into OpenPLC Runtime v4.
- **Author scenarios / train** — [`docs/SCENARIOS.md`](docs/SCENARIOS.md) · [`docs/TRAINER_GUIDE.md`](docs/TRAINER_GUIDE.md).

## Documentation
| Topic | Link |
|-------|------|
| Architecture | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) |
| Acceptance criteria | [`docs/ACCEPTANCE_CRITERIA.md`](docs/ACCEPTANCE_CRITERIA.md) |
| Roadmap · Changelog | [`docs/ROADMAP.md`](docs/ROADMAP.md) · [`docs/CHANGELOG.md`](docs/CHANGELOG.md) |
| Tag map · Scenarios · Faults | [`docs/TAG_MAP_MVP.md`](docs/TAG_MAP_MVP.md) · [`docs/SCENARIOS.md`](docs/SCENARIOS.md) · [`docs/FAULT_SCENARIOS.md`](docs/FAULT_SCENARIOS.md) |
| Deployment | [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) |
| Decisions (ADRs) | [`adr/`](adr) |
| Contributing | [`CONTRIBUTING.md`](CONTRIBUTING.md) |

## License
[MIT](LICENSE) — © 2026 OpenLogiTwin contributors.
