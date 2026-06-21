# Changelog

All notable changes to OpenLogiTwin. Grouped by development phase (the project predates
formal release tags). Dates are UTC.

## [0.3.0] — 2026-06-18

### Added
- **Multi-parcel FIFO cell** (ADR-0005): `tags.sorting_cell_advanced.json` (8-slot destination
  ring), cell-aware `ScenarioRunner` / `scenario_manager` (the scenario `cell` field selects the
  profile), `scenarios/dense_sort_advanced.json`, and `tests/test_advanced_cell.py`. Densely-spaced
  parcels route correctly — the advanced cell sorts a dense stream 4/4 where the MVP single
  register mis-routes it 2/6.
- **Community health & first release**: `CODE_OF_CONDUCT.md`, `SECURITY.md`, GitHub issue/PR
  templates. Published to GitHub with CI green across Python 3.9–3.13 × Ubuntu/Windows.

### Changed
- Framed as a "digital twin"; `pyproject` version → 0.3.0. MVP cell behaviour unchanged
  (determinism preserved).

## [Unreleased]

## [0.5.0] — 2026-06-20

External-runtime release: the twin is verified against **real FUXA and OpenPLC** (in Docker) and a
**Godot 3D scene**, with every finding folded back into the repo. Track A closes with Modbus
robustness.

### Added
- **OpenPLC behavioural equivalence** (B2): `plc/examples/03_sorting_cell_commissioning.st` puts
  inputs on master-writable coils/registers so the gateway can drive a real OpenPLC;
  `tests/test_openplc_behavioral.py` asserts it sorts identically to the soft-PLC.
- **Godot 3D scene** (B3): `simulation/godot-project/cell.tscn` + `cell.gd` author the cell; verified
  on Godot 4.2 headless (imports/runs, bridge connects, drives real sorts over Modbus).
  `tests/test_godot_project.py` drift-guards the bridge addresses.
- **FUXA mimic screen** (B1): `scripts/generate_fuxa_view.py` builds an SVG mimic and injects a
  bound `hmi.views[0]` (5 live readouts) into the FUXA project. `tests/test_fuxa_view.py`.
- **Modbus robustness** (A8, ADR-0008): `ModbusTCPClient` auto-reconnects once on a dropped socket;
  new `uint32` / `float32` multi-word register types (big-endian codec + word-aware `TagGateway`).
  `tests/test_modbus_robustness.py`.

### Fixed
- **OpenPLC ST compile**: `02_sorting_cell_mvp.st` now compiles on MatIEC — located and internal
  variables are split into separate VAR blocks and a `CONFIGURATION`/`RESOURCE`/`TASK` is appended.
- **Godot bridge load**: `cell_bridge.gd` preloads `modbus_client.gd` instead of the global
  `class_name`, so the autoload resolves on a fresh headless import.

### Verified (real runtimes, in Docker)
- FUXA v1.3.3 connects to the twin over Modbus and reads live values; OpenPLC Runtime v3 runs the
  compiled ST and matches the soft-PLC; Godot 4.2 headless drives real sorts. See
  `hmi/fuxa/INTEGRATION.md`, `plc/examples/README.md`, `simulation/godot-project/README.md`.

## [0.4.0] — 2026-06-20

Hardening & integration release: the three protocols are now exercised end-to-end (MQTT streaming
from the CLI, a full control loop over OPC UA), a richer scenario gallery, per-parcel barcodes, a
performance baseline, and a proper GitHub Pages landing page.

### Added
- **OPC UA full control loop** (A7): `opcua_adapter` gains a `server_to_store` / `store_to_server`
  bridge so a complete sorting cycle runs **end-to-end over OPC UA** — the gateway writes
  sensors/inputs and reads actuators/counters over the wire while the soft-PLC scans the mirrored
  process image. `tests/test_opcua_full_loop.py` (skips without `asyncua`).
- **Per-parcel barcode simulator** (`simulation/barcode.py`): a parcel can be injected by
  `barcode` instead of a raw chute; `BarcodeDecoder` maps it to a destination (explicit routes →
  valid **EAN-13** parity → alpha prefix) and a `barcode_scan` telemetry event is logged at the
  scan point. Scenario `barcode_routing` + `tests/test_barcode.py`.
- **Scenario gallery + control robustness**: scenarios `back_to_back_sort`, `motor_never_starts`,
  `two_jams`, `estop_during_divert`. uint16 counters now wrap explicitly (match the Modbus
  register); E-stop/Stop void the in-flight routing decision (`pending`) so recovery never acts on
  a stale decision. `tests/test_control_logic_mvp.py` covers the counter wrap.
- **MQTT telemetry** (third protocol, ADR-0007): `telemetry/mqtt_publisher.py`
  (`MqttTelemetryPublisher`) publishes telemetry events to `"{prefix}/{scenario}/{event_type}"`;
  `TelemetryLogger` gains an optional `sink=` hook, threaded through `ScenarioRunner`; a
  `--mqtt-host=HOST[:PORT]` flag on `scenario_manager` / `run_full_demo` streams telemetry live.
  Optional `paho-mqtt`; pure formatting + sink tests run with no broker, real round-trip verified
  against paho-mqtt + amqtt.
- **OPC UA adapter** (second protocol, ADR-0006): real `asyncua`-backed `OpcUaClient` +
  `build_opcua_server` helper, wired into `protocol_factory` (`kind="opcua"`). The same
  `TagGateway` runs over Modbus, in-process, pymodbus, **and OPC UA**. Optional dep; skip-by-default
  `tests/test_opcua_adapter.py` (verified vs asyncua 2.0). Replaces the OPC UA stub.
- **GitHub Pages**: `.github/workflows/pages.yml` publishes the demo report on every push to main
  → https://aydogandagidir.github.io/conveyor-sorting-twin/

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
