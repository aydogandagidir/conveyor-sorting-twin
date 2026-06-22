# OpenLogiTwin — Roadmap

Status legend: ✅ done & verified · 🟡 in progress · ⬜ planned · 🔒 deferred (needs external runtime).

## Phases (master-prompt plan) — complete
| Phase | Scope | Status |
|-------|-------|--------|
| **0 — PoC Connectivity** | Real Modbus TCP loop, tag registry, soft-PLC stub, telemetry | ✅ 19/19 |
| **1 — MVP Scene** | Deterministic sorting cell: routing, jam, counters, scenarios | ✅ 14/14 |
| **1.5 — Hardening** | CI, pytest, control unit tests, E-stop NC fail-safe, Modbus exceptions, multi-parcel FIFO | ✅ |
| **2 — HMI + Scenario Manager** | Scenario manager CLI, fault/control scenarios, protocol adapters, FUXA tag list + project | ✅ (FUXA SVG mimic generated + verified) |
| **3 — Productization** | Demo + report, deployment, sample OpenPLC ST, training docs, docs polish | ✅ |

## Protocol roadmap (stack direction) — 3/3
1. **Modbus TCP** ✅ — in-repo server/client + pymodbus adapter (ADR-0002).
2. **OPC UA** ✅ — real `asyncua` adapter (ADR-0006).
3. **MQTT telemetry** ✅ — telemetry sink `telemetry/mqtt_publisher.py` (ADR-0007).

## Beyond the master plan — done
- **Stage 2** — multi-parcel FIFO cell promoted to first-class (`tags.sorting_cell_advanced.json`,
  cell-aware runner/manager, `dense_sort_advanced` scenario) — ADR-0005.
- **Stage 3** — community health (CODE_OF_CONDUCT, SECURITY, issue/PR templates) + **v0.3.0** release.
- **Track A / v0.4.0** — hardening & integration (see below): MQTT-from-CLI, scenario gallery,
  control robustness, barcode simulator, performance baseline, Pages landing, OPC UA full loop.
- **GitHub Pages** — project landing + auto-published demo report: https://aydogandagidir.github.io/conveyor-sorting-twin/
- 28 test files green (pytest 99 passed, 7 optional backend skips); CI matrix Python 3.9/3.11/3.13 × Ubuntu/Windows.

## Track A — hardening & integration (done in v0.4.0)
Each landed via branch → PR → CI → merge.
- ✅ MQTT CLI integration (`--mqtt-host` on scenario manager / demo) — verified vs a real broker.
- ✅ Scenario gallery (`back_to_back_sort`, `two_jams`, `motor_never_starts`, `estop_during_divert`).
- ✅ Control robustness (uint16 counter wrap; E-stop/Stop void the in-flight routing decision).
- ✅ Per-parcel barcode simulator (`simulation/barcode.py`, EAN-13) + `barcode_scan` telemetry.
- ✅ Performance/throughput test + `docs/PERFORMANCE.md` baseline.
- ✅ Richer GitHub Pages landing page (`web/index.html`).
- ✅ OPC UA full-loop bridge — a full sorting cycle runs end-to-end over OPC UA.
- ✅ Modbus robustness (v0.5.0) — `ModbusTCPClient` auto-reconnects once on a dropped socket;
  `uint32`/`float32` multi-word register types via a codec + word-aware gateway
  (ADR-0008, `tests/test_modbus_robustness.py`).

## Track B — external runtimes (verified headlessly in Docker, 2026-06-20)
- ✅ **Real OpenPLC Runtime** — `02_sorting_cell_mvp.st` compiles + runs (connectivity harness
  passes); `03_sorting_cell_commissioning.st` is driven over Modbus and **matches the soft-PLC**
  (`tests/test_openplc_behavioral.py`). Found+fixed a MatIEC compile bug (separate VAR blocks).
- ✅ **FUXA HMI** — data path verified (the generated project connects + polls the twin, live values
  propagate); mimic SVG screen generated + injected, FUXA persists it with 5 readouts bound to the
  device tags (`scripts/generate_fuxa_view.py`, drift-guarded by `tests/test_fuxa_view.py`).
- ✅ **Godot 3D scene** — `cell.tscn` + `cell.gd` author the cell; verified on Godot 4.2 headless
  (imports + runs with 0 errors, bridge connects, drives real sorts over Modbus). `scene_model.py`
  stays the deterministic oracle; visual polish is editor work. Drift-guarded by `tests/test_godot_project.py`.

## Web HMI — browser operator console (done, v0.6.0)
A zero-install, browser-based **ANSI/ISA-101 high-performance HMI** for the sorting cell. Built
V0→V3, each via branch → PR → CI → merge; published on GitHub Pages (replay) at
https://aydogandagidir.github.io/conveyor-sorting-twin/hmi/
- ✅ **Trace export (V0)** — `scripts/export_trace.py` writes deterministic `web/hmi/traces/*.json`
  from the same `ScenarioRunner` the suite uses (`tests/test_trace_export.py`).
- ✅ **Web HMI (V1–V2)** — `web/hmi/` replays traces; redesigned to the High-Performance HMI
  doctrine (gray canvas, colour only for live data/alarms, status by brightness + word).
- ✅ **ISA-18.2 alarms + faceplates + nav + theme** — docked banner + alarm summary, equipment
  faceplates with rationalisation, L1/L2/L3 display hierarchy, light/dark theme. Drift-guarded by
  `tests/test_web_hmi.py`.
- ✅ **Live mode (V3)** — `scripts/hmi_server.py` streams the running twin over a hand-rolled stdlib
  WebSocket (RFC 6455); the HMI's process buttons drive the real soft-PLC. `tests/test_hmi_server.py`.

## Next — v0.7.0 productization (planned)
- ⬜ One-command launcher + onboarding (single entry point that starts the live server and opens the
  HMI), packaging/distribution, and a guided first-run. See `sprints/SPRINT_BACKLOG.md`.
