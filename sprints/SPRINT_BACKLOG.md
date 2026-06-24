# OpenLogiTwin — Sprint Backlog

> **Historical planning log**, frozen around v0.6.0. For current project status and what's next,
> see [`docs/ROADMAP.md`](../docs/ROADMAP.md) and [`docs/CHANGELOG.md`](../docs/CHANGELOG.md).

## Done — Phase 0 (PoC Connectivity)
- [x] Repo structure + scaffolding.
- [x] Tag registry schema + instance (12 tags, conveyor sorting cell).
- [x] Minimal standards-compliant Modbus TCP (server/client/data store).
- [x] Protocol gateway (tag ↔ Modbus, backend-agnostic).
- [x] Soft-PLC stub (Modbus slave + control scan).
- [x] Conveyor sorting control logic (E-stop, motor, routing, throughput).
- [x] Local control fallback (in-process, no sockets).
- [x] Telemetry logger (SQLite + CSV/JSON export).
- [x] Verification script proving Engineering Gate 1 (19/19 PASS).
- [x] Demo + standalone soft-PLC runner.
- [x] Docs (architecture, acceptance criteria, run guide) + ADR 0001/0002.

## Done — Phase 1 (MVP Scene)
- [x] Deterministic scene adapter (`simulation/scene_model.py`) + Godot docs.
- [x] MVP tag registry (`tags.sorting_cell_mvp.json`) on the Phase 0 model.
- [x] MVP control program (`control_logic_mvp.py`) via generalised `SoftPlc(control=...)`.
- [x] Lock-step scenario runner (`simulation/scenario_runner.py`) over Modbus TCP.
- [x] Virtual parcel generator + barcode/destination assignment.
- [x] Sensor events (pe_001, pe_002), motor + diverter actuation, 2 chutes + counters.
- [x] Jam fault: detection (pe_002 stuck timer) + reset/recovery.
- [x] Scenarios: `barcode_sorting_basic.json`, `jam_recovery_basic.json`.
- [x] HMI FUXA tag list, telemetry schema doc, `tests/verify_phase1.py` (14/14).

## Done — Phase 1.5 (Hardening)
- [x] CI workflow + `pyproject.toml` (Python 3.9–3.13 × Ubuntu/Windows).
- [x] Scenario schema + fail-fast validation; control-logic unit tests (13).
- [x] E-stop fail-safe (tag `invert`, NC de-energize-to-trip) + diverter-latch clear on
      E-stop (ADR-0004).
- [x] Modbus protocol exception + batch-FC tests (1.5d, 12/12).
- [x] pytest harness (conftest + phase gates) + `scripts/run_tests.py` (1.5e).
- [x] Multi-parcel destination FIFO-ring prototype + ADR-0005 (1.5f, 2/2).
- [x] Quick wins: deleted `docs_PLACEHOLDER.md`; `--export-dir`; protocol/telemetry READMEs.

Full suite: `python scripts/run_tests.py` → SUITE GREEN (all files).
Deferred (per decision): Godot 3D wiring; real OpenPLC ST/LD migration.

## Done — Phase 3 (Productization, verifiable parts)
- [x] Demo runner + self-contained HTML/Markdown report (`run_full_demo.py` +
      `generate_demo_report.py`, `tests/test_demo_report.py`) — 3c.
- [x] Telemetry write hardening (SQLite errors no longer crash the sim).
- [x] Deployment: `docs/DEPLOYMENT.md`, `Dockerfile`, `.dockerignore`, `.env.example`,
      profiled `docker-compose.yml` (validated by `docker compose config`) — 3a.
- [x] Sample OpenPLC ST programs + README + structural lint + OpenPLC connectivity harness — 3b.
- [x] Training docs: `TRAINER_GUIDE.md`, `FAULT_SCENARIOS.md`, `SCENARIOS.md` — 3b.
- [x] Docs polish: `ROADMAP.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `LICENSE` (MIT) — 3d.

## Done — Stage 2 (multi-parcel FIFO cell rollout, ADR-0005)
- [x] Promoted the FIFO-ring prototype to a first-class cell: `tags.sorting_cell_advanced.json`.
- [x] Cell-aware `ScenarioRunner` (`control` + `dest_strategy`) and `scenario_manager`
      (`cell` field → profile); MVP path unchanged (determinism preserved).
- [x] `scenarios/dense_sort_advanced.json` (8 parcels @0.4 s) + `tests/test_advanced_cell.py`
      (advanced 4/4 vs MVP single-register 2/6 on the same dense stream).

## Done — Track B external runtimes (verified headlessly in Docker, 0.5.0)
- [x] FUXA v1.3.3 — generated project connects + polls the twin; SVG mimic injected with bound
      readouts (`generate_fuxa_view.py`, `tests/test_fuxa_view.py`).
- [x] OpenPLC Runtime v3 — compiled ST driven over Modbus matches the soft-PLC
      (`tests/test_openplc_behavioral.py`).
- [x] Godot 4.2 headless — `cell.tscn` + `cell.gd` import/run and drive real sorts
      (`tests/test_godot_project.py`).

## Done — Web HMI (V0–V3, v0.6.0)
- [x] Deterministic trace export (`scripts/export_trace.py`, `tests/test_trace_export.py`).
- [x] ANSI/ISA-101 high-performance web HMI (`web/hmi/`): trace replay, ISA-18.2 alarms,
      faceplates, L1/L2/L3 hierarchy, light/dark theme — drift-guarded by `tests/test_web_hmi.py`.
- [x] Live mode: `scripts/hmi_server.py` streams the twin over a stdlib WebSocket; HMI buttons
      drive the real soft-PLC (`tests/test_hmi_server.py`).

## Decisions (resolved by user)
- **Hardening-first** sequencing (Phase 1.5 before Phase 2 features).
- **Keep custom Modbus + add pymodbus adapter** (Phase 2, additive via factory).
- **Keep soft-PLC stub through Phase 2**; real OpenPLC port deferred (after E-stop fail-safe).

## Done — Phase 2 (HMI + Scenario Manager)
- [x] Scenario manager CLI (`scripts/scenario_manager.py`): list / validate / run / run-all
      with `expect` checks.
- [x] Fault-injection + control scenarios (E-stop, Stop, rapid jam/reset) with expectations.
- [x] Start / stop / reset / E-stop controls exercised via scenarios + CLI.
- [x] Protocol extensibility: `protocol_factory` + pymodbus adapter (vs 3.13) + **real OPC UA**
      adapter (asyncua, ADR-0006) + **MQTT telemetry** sink (ADR-0007).
- [x] FUXA tag-list generator (registry-derived, drift-guarded) + project generator + `INTEGRATION.md`.
- [x] FUXA mimic SVG screen generated + injected + drift-guarded (`generate_fuxa_view.py`, B1).

## Done — Stage 3 (release & community)
- [x] Community health: `CODE_OF_CONDUCT.md`, `SECURITY.md`, issue/PR templates.
- [x] **v0.3.0** release + GitHub Pages (demo report auto-published).

## Protocol roadmap (per stack direction)
1. Modbus TCP — **done** (in-repo + pymodbus adapter).
2. OPC UA — **done** (real `asyncua` adapter, ADR-0006).
3. MQTT telemetry — **done** (telemetry sink `telemetry/mqtt_publisher.py`, ADR-0007).
