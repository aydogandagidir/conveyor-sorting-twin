# ADR-0003 — Phase 1 scene adapter and MVP cell

- Status: Accepted
- Date: 2026-06-17
- Phase: 1 (MVP Scene)

## Context
Phase 1 must deliver a conveyor sorting cell scene with deterministic scenarios,
destination-based diverting, chute counters, and jam trigger/reset — reusing the
Phase 0 tag-registry model. Godot cannot run headless in this environment, and the
acceptance criteria require *deterministic* runs.

## Decision
1. **Headless deterministic scene adapter in Python** (`simulation/scene_model.py`)
   is the authoritative plant for Phase 1; the Godot scene is documented
   (`docs/GODOT_SCENE.md`) as a visualization layer over the same tags. The Phase 1
   prompt explicitly allows "scene adapter **or** Godot scene documentation"; we
   deliver both, with the adapter as the test oracle.
2. **New MVP tag registry** (`tags.sorting_cell_mvp.json`) with the prompt's
   ISA-style names, mapped under the same Modbus master/slave semantics as Phase 0.
3. **Generalised soft-PLC**: `SoftPlc` now accepts a `control` module. Phase 0
   keeps `control_logic.py`; Phase 1 uses `control_logic_mvp.py`. No Phase 0 break.
4. **Lock-step scenario runner** (`simulation/scenario_runner.py`) drives the PLC
   scan manually (one scan per dt, no background thread) over the real Modbus
   gateway, so results are reproducible. A `--local` in-process mode exists too.
5. **Count on pe_002 falling edge** (decision latched on the rising edge): a parcel
   that jams at the eye never falls, so it is not counted — keeping PLC counters
   consistent with parcels that actually clear the diverter.

## Rationale
- Determinism is a hard acceptance criterion; a fixed-dt headless model gives a
  bit-identical re-run (asserted by `tests/verify_phase1.py`).
- Reusing Phase 0 infrastructure (Modbus, gateway, registry, telemetry) avoids
  duplication and keeps a single integration contract for the future Godot/OpenPLC
  swap.
- The `control` parameter is the minimal seam that lets two cells coexist.

## Consequences
- Two registries/control programs now exist (Phase 0 demo cell + Phase 1 MVP cell).
  Both are verified independently; `verify_phase1.py` also re-runs Phase 0.
- The shared `data.parcel_destination` register assumes a single parcel in the
  scan→divert region at a time; Phase 1 scenarios space parcels accordingly.
  Per-parcel destination tracking is a future enhancement.
- Under a jam, the PLC counter and the physical chute can differ for the jammed
  parcel (counted only on clearing); documented and covered by the jam scenario.

## Alternatives considered
- **Build the Godot scene now**: rejected for Phase 1 — non-deterministic and not
  runnable headless here; deferred to the visualization step.
- **Replace Phase 0 control logic in place**: rejected; extending via the `control`
  seam preserves the Phase 0 proof.
