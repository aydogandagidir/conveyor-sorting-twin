# OpenLogiTwin — Conveyor Sorting Cell Digital Twin

[![CI](https://github.com/aydogandagidir/conveyor-sorting-twin/actions/workflows/verify.yml/badge.svg)](https://github.com/aydogandagidir/conveyor-sorting-twin/actions/workflows/verify.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](pyproject.toml)
[![runtime deps: stdlib only](https://img.shields.io/badge/runtime%20deps-stdlib%20only-success.svg)](#quickstart)
[![live demo report](https://img.shields.io/badge/live-demo%20report-8a2be2.svg)](https://aydogandagidir.github.io/conveyor-sorting-twin/)

[![OpenLogiTwin web HMI — ANSI/ISA-101 high-performance operator console](web/hero.svg)](https://aydogandagidir.github.io/conveyor-sorting-twin/hmi/)

<p align="center"><a href="https://aydogandagidir.github.io/conveyor-sorting-twin/hmi/"><b>▶ Open the live web HMI</b></a> — ISA-101 operator console (replay in the browser, or go live over WebSocket)</p>

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
- **Tested & green** — 28 dual-mode test files run by one stdlib command and a
  Python 3.9–3.13 × Ubuntu/Windows CI matrix.
- **Browser HMI (ANSI/ISA-101)** — a zero-install, high-performance web operator console:
  replays deterministic traces, or goes **live** over a stdlib WebSocket to drive the running twin.

## Architecture
```
virtual sensor event → tag registry → protocol gateway (Modbus TCP)
   → soft-PLC control logic → actuator output → scene reads output
   → telemetry event (SQLite → CSV/JSON)
```
The gateway is backend-agnostic (in-repo Modbus, in-process, or pymodbus); the soft-PLC takes a
swappable control program and is a documented stand-in for **OpenPLC Runtime v3**.
Full design: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) · decisions: [`adr/`](adr).

## Quickstart
```bash
git clone https://github.com/aydogandagidir/conveyor-sorting-twin.git
cd conveyor-sorting-twin

python -m openlogitwin             # ▶ launch the web HMI (replay + live) and open the browser
python -m openlogitwin test        # the full test suite → SUITE GREEN (no dependencies)
python -m openlogitwin demo        # run every scenario → telemetry/exports/demo_report.html
```
`python -m openlogitwin <command>` is the front door (`hmi` · `demo` · `scenarios` · `export` · `plc` · `test`); each also runs directly as `python scripts/<name>.py`. The core needs **no third-party packages** (Python 3.9+); `pip install -e .` adds an `openlogitwin` console command (`pytest` / `pymodbus` are optional dev extras).

**New here?** Walk through the [**5-minute tour**](GETTING_STARTED.md) → run it, drive the HMI, go live.

## Status
| Phase | Scope | State |
|-------|-------|-------|
| 0 — PoC Connectivity | real Modbus TCP loop, tag registry, soft-PLC, telemetry | ✅ 19/19 |
| 1 — MVP Scene | deterministic sorting cell: routing, jam, counters | ✅ 14/14 |
| 1.5 — Hardening | CI, pytest, control unit tests, E-stop NC fail-safe, multi-parcel FIFO | ✅ |
| 2 — HMI + Scenario Manager | scenario CLI, fault scenarios, pymodbus adapter, FUXA mimic | ✅ |
| 3 — Productization | demo + report, deployment, sample OpenPLC ST, training docs | ✅ |
| Web HMI (V0–V3) | ISA-101 browser console: trace replay + live WebSocket mode | ✅ |

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
├── web/hmi/            # ISA-101 web HMI (trace replay + live WebSocket) + Pages landing
├── deployment/         # Dockerfile + profiled docker-compose + .env.example
├── tests/              # 28 dual-mode test files (run directly or via pytest)
├── openlogitwin/       # thin CLI front door: python -m openlogitwin (+ `openlogitwin` via pip -e)
├── scripts/            # start (launcher), run_tests, run_full_demo, scenario_manager, generators
└── docs/  adr/  sprints/
```

## Run it for real
- **Web HMI (ISA-101)** — `python scripts/export_trace.py` then `python -m http.server --directory web 8099` → open `/hmi/`. Live mode: `python scripts/hmi_server.py` and click **Go live**. See [`web/hmi/README.md`](web/hmi/README.md), or the hosted replay at [the live HMI](https://aydogandagidir.github.io/conveyor-sorting-twin/hmi/).
- **Soft-PLC over Modbus** — `python scripts/run_soft_plc.py`, or `docker compose -f deployment/docker-compose.yml --profile full up --build`.
- **HMI (FUXA)** — [`hmi/fuxa/INTEGRATION.md`](hmi/fuxa/INTEGRATION.md).
- **Real PLC** — load [`plc/examples/*.st`](plc/examples) into OpenPLC Runtime v3.
- **Author scenarios / train** — [`docs/SCENARIOS.md`](docs/SCENARIOS.md) · [`docs/TRAINER_GUIDE.md`](docs/TRAINER_GUIDE.md).

## Documentation
| Topic | Link |
|-------|------|
| **Getting started** | [`GETTING_STARTED.md`](GETTING_STARTED.md) — a 5-minute tour |
| Architecture | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) |
| Acceptance criteria | [`docs/ACCEPTANCE_CRITERIA.md`](docs/ACCEPTANCE_CRITERIA.md) |
| Roadmap · Changelog | [`docs/ROADMAP.md`](docs/ROADMAP.md) · [`docs/CHANGELOG.md`](docs/CHANGELOG.md) |
| Tag map · Scenarios · Faults | [`docs/TAG_MAP_MVP.md`](docs/TAG_MAP_MVP.md) · [`docs/SCENARIOS.md`](docs/SCENARIOS.md) · [`docs/FAULT_SCENARIOS.md`](docs/FAULT_SCENARIOS.md) |
| Deployment | [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) |
| Performance | [`docs/PERFORMANCE.md`](docs/PERFORMANCE.md) |
| Decisions (ADRs) | [`adr/`](adr) |
| Contributing | [`CONTRIBUTING.md`](CONTRIBUTING.md) |

## License
[MIT](LICENSE) — © 2026 OpenLogiTwin contributors.
