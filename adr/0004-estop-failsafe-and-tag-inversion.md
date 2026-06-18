# ADR-0004 — E-stop fail-safe and tag inversion

- Status: Accepted
- Date: 2026-06-17
- Phase: 1.5 (Hardening)

## Context
The Phase 1 MVP control program models the E-stop **active-true** (`input.estop = true`
means engaged). Real industrial E-stops are **normally-closed (NC), de-energize-to-trip**:
the wire reads TRUE when healthy and FALSE when the button is pressed *or the wire breaks*.
Porting to real OpenPLC / hardware without accounting for this would invert the safety
logic — a pressed E-stop could *enable* the motor (a critical failure). Flagged by the
Phase 1.5 control-logic analysis.

## Decision
Add an optional per-tag boolean **`invert`** (bool tags only) to the tag registry.
The soft-PLC applies it at the **I/O boundary** (`plc/soft_plc.py:_read_tag/_write_tag`):
an inverted input is presented to the control program as its logical value
(`logical = not raw_wire`). The control logic (`control_logic_mvp.py`) is unchanged.

- **Real NC E-stop:** mark `input.estop` with `"invert": true`, `"initial": true`.
  Raw wire true (healthy) → control sees engaged=false → run permitted. Wire false
  (pressed/broken) → control sees engaged=true → motor stops. **Fail-safe.**
- **Simulation default:** the Phase 1 MVP registry keeps active-true (`invert` absent →
  false) for authoring convenience; scenarios set `input.estop=true` to engage.

Also (safety hardening): the control program now clears the diverter latch on
E-stop/Stop (`control_logic_mvp.py`), so the actuator is never left latched while stopped.

## Rationale
- Conditioning at the I/O boundary mirrors real PLC practice (inputs are marked
  inverted in the I/O config), keeps the control program portable to OpenPLC unchanged,
  and is a reusable capability (any bool input/output can be inverted).
- Non-breaking: existing registries omit `invert` (defaults false); Phase 0/1 stay green.

## Consequences
- A fail-safe E-stop uses the de-energize-to-trip convention (`initial: true`,
  engage by writing false) — documented; scenario authors must use it for NC tags.
- `invert` applies to bool tags only; register tags ignore it.

## Verification
- `tests/test_estop_failsafe.py`: healthy wire runs; de-energized wire stops (invert=true);
  active-true variant still works (invert=false).
- `tests/test_control_logic_mvp.py::test_estop_clears_diverter_latch`.
- `tests/verify_phase0.py` and `tests/verify_phase1.py` remain 19/19 and 14/14.

## Alternatives considered
- **Invert inside control_logic_mvp.py:** rejected; couples safety convention to the
  program and would break the active-true simulation scenarios.
- **Invert in the gateway (master side):** rejected; inversion is a property of the PLC
  input wiring, so the slave/PLC boundary is the correct place.
