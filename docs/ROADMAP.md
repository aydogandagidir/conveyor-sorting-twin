# OpenLogiTwin — Roadmap

Status legend: ✅ done & verified · 🟡 in progress · ⬜ planned · 🔒 deferred (needs external runtime).

## Phases (master-prompt plan) — complete
| Phase | Scope | Status |
|-------|-------|--------|
| **0 — PoC Connectivity** | Real Modbus TCP loop, tag registry, soft-PLC stub, telemetry | ✅ 19/19 |
| **1 — MVP Scene** | Deterministic sorting cell: routing, jam, counters, scenarios | ✅ 14/14 |
| **1.5 — Hardening** | CI, pytest, control unit tests, E-stop NC fail-safe, Modbus exceptions, multi-parcel FIFO | ✅ |
| **2 — HMI + Scenario Manager** | Scenario manager CLI, fault/control scenarios, protocol adapters, FUXA tag list + project | ✅ (FUXA SVG screens = external) |
| **3 — Productization** | Demo + report, deployment, sample OpenPLC ST, training docs, docs polish | ✅ |

## Protocol roadmap (stack direction) — 3/3
1. **Modbus TCP** ✅ — in-repo server/client + pymodbus adapter (ADR-0002).
2. **OPC UA** ✅ — real `asyncua` adapter (ADR-0006).
3. **MQTT telemetry** ✅ — telemetry sink `telemetry/mqtt_publisher.py` (ADR-0007).

## Beyond the master plan — done
- **Stage 2** — multi-parcel FIFO cell promoted to first-class (`tags.sorting_cell_advanced.json`,
  cell-aware runner/manager, `dense_sort_advanced` scenario) — ADR-0005.
- **Stage 3** — community health (CODE_OF_CONDUCT, SECURITY, issue/PR templates) + **v0.3.0** release.
- **GitHub Pages** — demo report auto-published: https://aydogandagidir.github.io/conveyor-sorting-twin/
- 17 test files green (pytest 54 passed, 6 optional skips); CI matrix Python 3.9–3.13 × Ubuntu/Windows.

## Remaining — Track A (verifiable here, planned)
Optional hardening/enhancements; each lands via branch → PR → CI → merge (see the approved plan).
- ⬜ MQTT CLI integration (`--mqtt-host` on scenario manager / demo).
- ⬜ Scenario gallery (back-to-back, two jams, motor-never-starts, estop-during-divert).
- ⬜ Control robustness (uint16 counter overflow; optional soft jam recovery).
- ⬜ Per-parcel barcode simulator (`simulation/barcode.py`).
- ⬜ Performance/throughput test + `docs/PERFORMANCE.md` baseline.
- ⬜ Richer GitHub Pages landing page.
- ⬜ OPC UA full-loop bridge (run a scenario end-to-end over OPC UA).
- ⬜ (Optional) Modbus connection health/reconnect; multi-word register types.

## Remaining — Track B (needs an external runtime; scaffolds + guides ready)
- 🔒 **FUXA SVG mimic screens** — import `generate_fuxa_project.py` output, draw mimic, bind widgets
  (`hmi/fuxa/INTEGRATION.md`). Optional docker/Selenium e2e smoke test.
- 🔒 **Real OpenPLC Runtime v4** — load `plc/examples/02_sorting_cell_mvp.st`, configure the Modbus
  slave, run the connectivity harness (`OPENPLC_HOST=... python tests/test_openplc_integration.py`).
- 🔒 **Godot 3D scene** — author the `.tscn` per `docs/GODOT_SCENE.md`; wire physics to `cell_bridge.gd`.
  `scene_model.py` stays the deterministic test oracle.
