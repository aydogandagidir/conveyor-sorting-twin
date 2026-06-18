# Changelog

All notable changes to OpenLogiTwin. Grouped by development phase (the project predates
formal release tags). Dates are UTC.

## [Unreleased]

### Phase 3 — Productization (in progress) · 2026-06-17
- Added one-command demo runner `scripts/run_full_demo.py` (runs the scenario suite,
  aggregates throughput/sort/fault metrics) and `scripts/generate_demo_report.py`
  (self-contained HTML + Markdown report). Covered by `tests/test_demo_report.py`.
- Hardened telemetry: SQLite write failures are logged to stderr instead of crashing the run.
- Docs: `ROADMAP.md`, this `CHANGELOG.md`, `CONTRIBUTING.md`.

### Phase 2 — HMI + Scenario Manager · 2026-06-17
- Added scenario manager CLI `scripts/scenario_manager.py` (`list` / `validate` / `run` /
  `run-all`, checks each scenario `expect` block).
- Added fault/control scenarios: `estop_during_run`, `stop_button_basic`, `rapid_jam_reset`.
- Added protocol extensibility: `protocol-gateway/protocol_factory.py`,
  `adapters/pymodbus_adapter.py` (verified vs pymodbus 3.13), and OPC UA / MQTT stubs.
- Added FUXA tag-list generator `scripts/generate_hmi_tag_list.py` (registry-derived,
  drift-guarded) and `hmi/fuxa/INTEGRATION.md`.

### Phase 1.5 — Hardening · 2026-06-17
- Added CI workflow (`.github/workflows/verify.yml`, Python 3.9–3.13 × Ubuntu/Windows) and
  `pyproject.toml`.
- Added control-logic unit tests, Modbus protocol exception tests, scenario schema validation,
  and a pytest harness (`tests/conftest.py`, `tests/test_phase_gates.py`, `scripts/run_tests.py`).
- Added E-stop **NC fail-safe** via tag `invert` at the I/O boundary (ADR-0004); the control
  program now clears the diverter latch on E-stop/Stop.
- Added multi-parcel **FIFO ring** prototype `plc/control_logic_advanced.py` (ADR-0005).
- Removed the stale `docs_PLACEHOLDER.md`; added `--export-dir` to the runners.

### Phase 1 — MVP Scene · 2026-06-17
- Added the deterministic conveyor sorting cell: `simulation/scene_model.py` (1-D lock-step
  plant), `simulation/scenario_runner.py`, `plc/control_logic_mvp.py`, MVP tag registry.
- Added scenarios `barcode_sorting_basic` and `jam_recovery_basic`; verification 14/14.
- Generalised `SoftPlc` to accept a `control` module.

### Phase 0 — PoC Connectivity · 2026-06-17
- Initial Modbus TCP loop: `protocol-gateway/modbus_tcp.py` (subset server/client/data store),
  `tag_registry.py`, `gateway.py`, soft-PLC stub, SQLite telemetry with CSV/JSON export.
- Engineering Gate 1 proven end to end (19/19).

[Unreleased]: project history tracked by phase; see docs/ROADMAP.md for what's next.
