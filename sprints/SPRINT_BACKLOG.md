# OpenLogiTwin — Sprint Backlog

Updated as implementation evolves (Development Rule 10).

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

## Best-effort (verify in external tool) / deferred
- [~] FUXA project generator (`generate_fuxa_project.py`, structure-tested) + Godot 4.x
      scaffold (project + GDScript client/bridge). Import into FUXA / open in Godot to verify.
- 🔒 Live OpenPLC ST run, FUXA SVG screens, Godot `.tscn` scene — need the external runtime.

## Decisions (resolved by user)
- **Hardening-first** sequencing (Phase 1.5 before Phase 2 features).
- **Keep custom Modbus + add pymodbus adapter** (Phase 2, additive via factory).
- **Keep soft-PLC stub through Phase 2**; real OpenPLC port deferred (after E-stop fail-safe).

## In progress — Phase 2 (HMI + Scenario Manager)
- [x] Scenario manager CLI (`scripts/scenario_manager.py`): list / validate / run / run-all
      with `expect` checks.
- [x] Fault-injection + control scenarios (E-stop, Stop, rapid jam/reset) with expectations.
- [x] Start / stop / reset / E-stop controls exercised via scenarios + CLI.
- [x] Protocol extensibility: pymodbus adapter (verified vs pymodbus 3.13) + `protocol_factory`
      + OPC UA / MQTT stubs.
- [x] FUXA tag-list generator (registry-derived, drift-guarded) + `hmi/fuxa/INTEGRATION.md`.
- [ ] FUXA mimic project JSON (SVG screens) — authored & exported inside FUXA.

## Later — Phase 3 (Productization)
- [ ] Deployment/installer docs.
- [ ] Sample PLC programs (OpenPLC ST/LD).
- [ ] Training scenario docs.
- [ ] Demo script + exportable results.

## Protocol roadmap (per stack direction)
1. Modbus TCP — **done (Phase 0)**.
2. OPC UA — second.
3. MQTT telemetry — third (after core loop is solid).
