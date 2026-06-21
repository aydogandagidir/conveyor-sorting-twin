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
- **Track A / v0.4.0** — hardening & integration (see below): MQTT-from-CLI, scenario gallery,
  control robustness, barcode simulator, performance baseline, Pages landing, OPC UA full loop.
- **GitHub Pages** — project landing + auto-published demo report: https://aydogandagidir.github.io/conveyor-sorting-twin/
- 21 test files green (pytest 71 passed, 6 optional backend skips); CI matrix Python 3.9–3.13 × Ubuntu/Windows.

## Track A — hardening & integration (done in v0.4.0)
Each landed via branch → PR → CI → merge.
- ✅ MQTT CLI integration (`--mqtt-host` on scenario manager / demo) — verified vs a real broker.
- ✅ Scenario gallery (`back_to_back_sort`, `two_jams`, `motor_never_starts`, `estop_during_divert`).
- ✅ Control robustness (uint16 counter wrap; E-stop/Stop void the in-flight routing decision).
- ✅ Per-parcel barcode simulator (`simulation/barcode.py`, EAN-13) + `barcode_scan` telemetry.
- ✅ Performance/throughput test + `docs/PERFORMANCE.md` baseline.
- ✅ Richer GitHub Pages landing page (`web/index.html`).
- ✅ OPC UA full-loop bridge — a full sorting cycle runs end-to-end over OPC UA.
- ⬜ (Optional, low priority) Modbus connection health/reconnect; multi-word register types
  (uint32/float32). Not required for any current scenario.

## Track B — external runtimes (verified headlessly in Docker, 2026-06-20)
- ✅ **Real OpenPLC Runtime** — `02_sorting_cell_mvp.st` compiles + runs (connectivity harness
  passes); `03_sorting_cell_commissioning.st` is driven over Modbus and **matches the soft-PLC**
  (`tests/test_openplc_behavioral.py`). Found+fixed a MatIEC compile bug (separate VAR blocks).
- 🟡 **FUXA HMI** — data path verified: the generated project connects + polls the twin and live
  values propagate (`hmi/fuxa/INTEGRATION.md`). Mimic SVG screens: in progress (generated + injected).
- ⬜ **Godot 3D scene** — author the `.tscn` per `docs/GODOT_SCENE.md`, validate with Godot headless,
  wire the bridge to `cell_bridge.gd`. `scene_model.py` stays the deterministic test oracle.
