"""Conveyor sorting cell control logic — the 'PLC program' for Phase 0.

Pure and transport-agnostic. The exact same scan() runs:
  - inside the soft-PLC stub (plc/soft_plc.py) over a Modbus data store, and
  - in the local control fallback for development.

It is deliberately simple for Phase 0. Parcel tracking, debounce and full jam
timing belong to Phase 1. This logic is replaceable by an OpenPLC ladder/ST
program later; see adr/0002.

Inputs (named tag values):
  estop                bool   True = emergency stop engaged
  sensor.preDivert     bool   parcel present at the divert decision point
  barcode.destination  int    decoded destination chute (1..3)
Outputs:
  motor.conveyor       bool
  diverter.armA        bool   route to chute 1
  diverter.armB        bool   route to chute 2
  fault.jam            bool   latched jam (auto-set logic is a Phase 1 TODO)
  indicator.running    bool
  throughput.count     int    parcels counted at the divert point
"""
from __future__ import annotations

DEST_CHUTE_1 = 1
DEST_CHUTE_2 = 2
DEST_CHUTE_3 = 3  # straight-through, no diverter


def initial_state() -> dict:
    return {"prev_preDivert": False, "throughput": 0, "jam_latched": False}


def scan(inputs: dict, state: dict):
    """Run one PLC scan. Returns (outputs, state)."""
    estop = bool(inputs.get("estop", False))
    pre_divert = bool(inputs.get("sensor.preDivert", False))
    destination = int(inputs.get("barcode.destination", 0) or 0)

    out = {
        "motor.conveyor": False,
        "diverter.armA": False,
        "diverter.armB": False,
        "fault.jam": bool(state.get("jam_latched", False)),
        "indicator.running": False,
        "throughput.count": int(state.get("throughput", 0)),
    }

    # --- Safety: E-stop overrides everything --------------------------------
    if estop:
        state["prev_preDivert"] = pre_divert
        return out, state

    # --- Jam latched: hold the conveyor stopped until the fault is cleared ---
    # Phase 0 never auto-sets the jam (TODO Phase 1: stuck-parcel scan timer).
    if out["fault.jam"]:
        state["prev_preDivert"] = pre_divert
        return out, state

    # --- Normal running -----------------------------------------------------
    out["motor.conveyor"] = True
    out["indicator.running"] = True

    # Routing decision at the divert point.
    if pre_divert:
        if destination == DEST_CHUTE_1:
            out["diverter.armA"] = True
        elif destination == DEST_CHUTE_2:
            out["diverter.armB"] = True
        # destination 3 (or unknown) -> straight through, no arm energised.

    # Throughput: count one parcel on the rising edge of the divert sensor.
    if pre_divert and not state.get("prev_preDivert", False):
        state["throughput"] = int(state.get("throughput", 0)) + 1
        out["throughput.count"] = state["throughput"]

    state["prev_preDivert"] = pre_divert
    return out, state
