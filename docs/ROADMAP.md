# OpenLogiTwin — Roadmap

Status legend: ✅ done & verified · 🟡 in progress · ⬜ planned · 🔒 deferred (needs external runtime).

| Phase | Scope | Status |
|-------|-------|--------|
| **0 — PoC Connectivity** | Real Modbus TCP loop, tag registry, soft-PLC stub, telemetry | ✅ 19/19 |
| **1 — MVP Scene** | Deterministic sorting cell, routing, jam, counters, scenarios | ✅ 14/14 |
| **1.5 — Hardening** | CI, pytest, control unit tests, E-stop NC fail-safe, Modbus exceptions, multi-parcel FIFO | ✅ |
| **2 — HMI + Scenario Manager** | Scenario manager CLI, fault/control scenarios, pymodbus adapter + stubs, FUXA tag list | 🟡 (FUXA mimic JSON pending) |
| **3 — Productization** | Demo + report, deployment, sample PLC programs, training docs, docs polish | 🟡 (3c done) |

## Phase 2 — remaining
- ⬜ FUXA mimic project JSON (SVG screens + widget bindings) — authored inside FUXA. The
  integration contract (auto-generated tag list + `hmi/fuxa/INTEGRATION.md`) is done.

## Phase 3 — sub-phases
- ✅ **3c Demo + results export** — `scripts/run_full_demo.py` + `generate_demo_report.py`
  (self-contained HTML/Markdown), `tests/test_demo_report.py`.
- ✅ **3a Deployment** — `docs/DEPLOYMENT.md`, `deployment/Dockerfile`, `.dockerignore`,
  `.env.example`, profiled `docker-compose.yml` (validated via `docker compose config`).
- ✅ **3b Sample programs + training** — `plc/examples/*.st` (OpenPLC ST port of
  `control_logic_mvp`) + lint, OpenPLC connectivity harness, `TRAINER_GUIDE.md`,
  `FAULT_SCENARIOS.md`, `SCENARIOS.md`.
- ✅ **3d Docs polish** — this file, `CHANGELOG.md`, `CONTRIBUTING.md`, `LICENSE` (MIT; changeable by owner).

## Best-effort artifacts (provided; verify in their tool)
- 🟡 **FUXA project** — `scripts/generate_fuxa_project.py` (registry-derived device + 12 tags,
  structure-tested). Import into FUXA to confirm; SVG mimic screens drawn in the editor.
- 🟡 **Godot 4.x scaffold** — `simulation/godot-project/project.godot` + `modbus_client.gd` +
  `cell_bridge.gd`. Open in Godot 4.x; author the `.tscn` per `docs/GODOT_SCENE.md`.

## Deferred — need an external runtime (not verifiable headless here)
- 🔒 **Real OpenPLC Runtime v4** — promote the ST program to a live OpenPLC slave; point the
  gateway at it (zero changes to runner/registry — see ADR-0002/0003). Decision: keep the
  soft-PLC stub through Phase 2.
- 🔒 **Godot 3D scene** — visualization over the same tag contract (`docs/GODOT_SCENE.md`);
  `scene_model.py` stays the deterministic test oracle.
- 🔒 **FUXA end-to-end test** — Selenium/docker smoke test once the mimic JSON exists.

## Cross-cutting (tracked)
- Multi-parcel FIFO (`control_logic_advanced`) is a verified prototype; promote to a default
  cell config before dense-throughput deployment (ADR-0005).
- pymodbus adapter is verified vs 3.13 but optional (CI skips when absent).
