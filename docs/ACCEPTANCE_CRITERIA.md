# OpenLogiTwin — Acceptance Criteria

This document tracks acceptance criteria per phase. It is updated as
implementation evolves.

Legend: `[x]` met & verified · `[~]` partial · `[ ]` not started.

---

## Phase 0 — PoC Connectivity

**Goal:** prove the Engineering Gate 1 loop end to end.

```
virtual sensor event -> tag registry -> protocol gateway -> PLC/control logic
-> actuator output -> simulation state update -> telemetry event
```

### Gate 1 — Required Proof
- [x] A virtual sensor boolean changes from false to true
      (`sensor.preDivert` driven by `simulation/cell_sim.py`).
- [x] The gateway exposes/receives this tag
      (`protocol-gateway/gateway.py` writes coil over **real Modbus TCP**).
- [x] PLC / local control logic responds
      (`plc/soft_plc.py` scan runs `plc/control_logic.py`).
- [x] A motor/diverter output tag changes
      (`motor.conveyor`, `diverter.armA/armB` flip in response).
- [x] The simulation layer receives the output
      (gateway reads `discrete_input`/`input_register` back).
- [x] A telemetry event is logged
      (`telemetry/telemetry_logger.py` → SQLite, exported to CSV/JSON).

### Phase 0 Deliverables
- [x] Repo structure created.
- [x] Tag registry JSON schema (`protocol-gateway/schema/tag_registry.schema.json`)
      + instance (`protocol-gateway/config/tags.conveyor_sorting_cell.json`).
- [x] Protocol gateway skeleton (`protocol-gateway/`).
- [x] Modbus TCP proof path (gateway master ↔ soft-PLC slave, real MBAP framing).
- [x] Local control fallback for development (`LocalStoreClient`, no sockets).
- [x] Telemetry logger (SQLite + CSV/JSON export).
- [x] Verification script (`tests/verify_phase0.py`, 19/19 checks PASS).

### How verified
```
python tests/verify_phase0.py      # exit 0, prints 19/19 PASS
python scripts/run_demo.py         # human-readable parcel routing + export
```

### Known limitations (Phase 0)
- Soft-PLC is a **stub** for OpenPLC Runtime v3 (clearly named; see ADR-0002).
- Modbus implementation is a standards-compliant **subset** (FC 1/2/3/4/5/6/15/16),
  not a full stack; swappable for pymodbus / OpenPLC (ADR-0002).
- Jam detection tag exists but auto-detection logic is deferred to Phase 1.
- Simulation is a Python stand-in; the Godot scene is Phase 1.
- No HMI yet (Phase 2); no OPC UA / MQTT yet (later protocol priorities).

---

## Phase 1 — MVP Scene  *(complete & verified)*

**Goal:** a minimal conveyor sorting cell path on the Phase 0 tag-registry model.

### Acceptance criteria (from the Phase 1 prompt)
- [x] User can run a deterministic scenario
      (`scripts/run_scenario.py`; verifier asserts a bit-identical re-run).
- [x] Parcels are assigned destinations
      (`data.parcel_destination` published at pe_001; A,B,A,B in the basic scenario).
- [x] Diverter output changes based on destination
      (`output.diverter_dv_001_extend` extends for CHUTE_A only).
- [x] Chute counters increment (`counter.sorted_chute_a/b` → 2 / 2 in basic).
- [x] Jam fault can be triggered and reset
      (`alarm.jam_001` latches, motor stops, reset clears + recovers).
- [x] Telemetry records cycle, sorting and fault events
      (`cycle`, `sort`, `fault`, `machine_state` — see `telemetry/SCHEMA.md`).

### Deliverables
- [x] Scene adapter (`simulation/scene_model.py`) **and** Godot docs (`docs/GODOT_SCENE.md`).
- [x] Tag mapping file (`tags.sorting_cell_mvp.json`, `docs/TAG_MAP_MVP.md`).
- [x] Scenario files: `scenarios/barcode_sorting_basic.json`, `scenarios/jam_recovery_basic.json`.
- [x] HMI tag list for FUXA (`hmi/fuxa/tag_list_sorting_cell_mvp.csv`).
- [x] Updated telemetry schema (`telemetry/SCHEMA.md` + logger helpers).
- [x] Updated verification script (`tests/verify_phase1.py`, 14/14 PASS incl. Phase 0 regression).

### How verified
```
python tests/verify_phase1.py          # exit 0, 14/14 (re-runs Phase 0 too)
python scripts/run_scenario.py scenarios/barcode_sorting_basic.json
python scripts/run_scenario.py scenarios/jam_recovery_basic.json
```

### Known limitations (Phase 1)
- Plant is the deterministic Python adapter; the Godot 3D scene is documented but
  not yet wired (visualization step).
- Control logic remains a stub for OpenPLC (`control_logic_mvp.py`).
- Shared `data.parcel_destination` assumes one parcel in the scan→divert region at
  a time; scenarios space parcels accordingly (per-parcel tracking is future work).
- A jammed parcel is counted only if it clears the diverter (by design).

## Phase 1.5 — Hardening  *(complete & verified)*

Per the approved development plan (hardening-first). All items verified locally;
CI activates on first git push.

- [x] CI workflow (`.github/workflows/verify.yml`, matrix Python 3.9/3.11/3.13 ×
      Ubuntu/Windows) + `pyproject.toml` (requires-python ≥3.9).
- [x] Scenario validation (`scenarios/schema.json` + `validate_scenario` fail-fast) —
      `tests/test_scenario_schema.py` (7/7).
- [x] Control-logic unit tests (`tests/test_control_logic_mvp.py`, 13/13).
- [x] E-stop fail-safe via tag `invert` (NC, de-energize-to-trip) + diverter-latch clear
      on E-stop — `tests/test_estop_failsafe.py` (2/2), ADR-0004.
- [x] Quick wins: removed stale `docs_PLACEHOLDER.md`; `--export-dir` flag;
      `protocol-gateway/README.md` (FC table); `telemetry/README.md`.
- [x] Modbus protocol exception tests + batch-FC round-trips
      (`tests/test_modbus_protocol.py`, 12/12) — 1.5d.
- [x] pytest harness: `tests/conftest.py` fixtures + `tests/test_phase_gates.py`;
      single-command `scripts/run_tests.py` (stdlib) — 1.5e.
- [x] Multi-parcel destination FIFO ring — `plc/control_logic_advanced.py` +
      `tests/test_multi_parcel_prototype.py` (2/2), ADR-0005 — 1.5f.

### Verified
```
python scripts/run_tests.py     # all test files -> SUITE GREEN
python -m pytest tests/ -q      # green (pytest 112 passed, 7 skipped at time of writing)
```

---

## Phase 2 — HMI + Scenario Manager  *(complete & verified)*

- [x] FUXA-compatible HMI template — device tag list auto-generated
      (`scripts/generate_hmi_tag_list.py`, drift-guarded) + a generated FUXA project
      (`scripts/generate_fuxa_project.py` → device + 12 tags, best-effort vs the FUXA model,
      structure-tested) + `hmi/fuxa/INTEGRATION.md` + `docker-compose` `hmi` profile.
      An SVG mimic screen is now generated + injected + drift-guarded
      (`scripts/generate_fuxa_view.py`, `tests/test_fuxa_view.py`).
- [x] Scenario JSON files — 5 scenarios incl. 3 fault/control
      (`estop_during_run`, `stop_button_basic`, `rapid_jam_reset`) with `expect` blocks.
- [x] Fault injection panel or CLI — `scripts/scenario_manager.py`
      (`list` / `validate` / `run` / `run-all`, checks each `expect`).
- [x] Start/stop/reset (+ E-stop) controls — exercised via scenarios/CLI.
- [x] Protocol extensibility (per decision) — `protocol-gateway/protocol_factory.py`
      + `adapters/pymodbus_adapter.py` (verified vs pymodbus 3.13) + **real OPC UA adapter**
      (`adapters/opcua_adapter.py`, verified vs asyncua 2.0, ADR-0006) + **MQTT telemetry sink**
      (`telemetry/mqtt_publisher.py`, ADR-0007).

### Verified
```
python scripts/scenario_manager.py run-all          # 5 scenarios, ALL EXPECTATIONS MET
python scripts/run_tests.py                          # all files -> SUITE GREEN
.venv/Scripts/python tests/test_pymodbus_adapter.py  # real pymodbus interop, 5/5
```

### Closed (Phase 2)
- [x] FUXA mimic SVG screen — generated + injected into the project and drift-guarded
      (`scripts/generate_fuxa_view.py`, `tests/test_fuxa_view.py`); FUXA persists it with 5
      readouts bound to the device tags (verified in Docker, 0.5.0).

## Phase 3 — Productization  *(verifiable parts complete)*
- [x] Demo script — `scripts/run_full_demo.py` (runs the scenario suite, aggregates metrics).
- [x] Exportable results — `scripts/generate_demo_report.py` → self-contained HTML + Markdown
      report (`telemetry/exports/demo_report.html`), verified by `tests/test_demo_report.py`.
- [x] Installer / deployment docs (3a) — `docs/DEPLOYMENT.md`, `deployment/Dockerfile`,
      `.dockerignore`, `.env.example`, profiled `docker-compose.yml` (validated via `compose config`).
- [x] Sample PLC programs (3b) — `plc/examples/01_basic_conveyor_latch.st`,
      `02_sorting_cell_mvp.st`, `README.md`; structural lint `tests/test_st_examples.py`;
      connectivity harness `tests/test_openplc_integration.py` (skips w/o `OPENPLC_HOST`).
- [x] Training scenario docs (3b) — `docs/TRAINER_GUIDE.md`, `docs/FAULT_SCENARIOS.md`, `docs/SCENARIOS.md`.
- [x] Docs polish (3d) — `docs/ROADMAP.md`, `docs/CHANGELOG.md`, `CONTRIBUTING.md`, `LICENSE` (MIT; changeable).

### External runtimes (verified headlessly in Docker, 0.5.0)
- [x] FUXA v1.3.3 — generated project connects + polls the twin over Modbus; SVG mimic injected
      with bound readouts (`scripts/generate_fuxa_view.py`, `tests/test_fuxa_view.py`).
- [x] OpenPLC Runtime v3 — `03_sorting_cell_commissioning.st` driven over Modbus matches the
      soft-PLC (`tests/test_openplc_behavioral.py`).
- [x] Godot 4.2 headless — `cell.tscn` + `cell.gd` import/run and drive real sorts over Modbus
      (`tests/test_godot_project.py`).

## Web HMI — browser operator console (V0–V3)  *(complete & verified)*
- [x] Deterministic trace export (`scripts/export_trace.py`, `tests/test_trace_export.py`).
- [x] ANSI/ISA-101 high-performance web HMI replaying traces; ISA-18.2 alarms, faceplates,
      L1/L2/L3 hierarchy, light/dark theme — drift-guarded by `tests/test_web_hmi.py`.
- [x] Live mode: `scripts/hmi_server.py` streams the running twin over a stdlib WebSocket and the
      HMI's buttons drive the real soft-PLC (`tests/test_hmi_server.py`). Browser-verified end to end.

### Verified (3a/3b/3c)
```
python scripts/run_full_demo.py                                   # 7 parcels, expect 5/5, HTML+MD report
docker compose -f deployment/docker-compose.yml --profile full config   # valid
python scripts/run_tests.py                                       # all files -> SUITE GREEN
```
