"""MVP conveyor sorting cell control program (Phase 1).

Same (initial_state, scan) contract as plc/control_logic.py, so it plugs into
plc/soft_plc.py via the `control` parameter. Still a STUB stand-in for an OpenPLC
ST/LD program (ADR-0002 / ADR-0003).

Inputs (sim_to_plc):
  sensor.pe_001            bool    infeed / barcode-scan photo-eye
  sensor.pe_002            bool    pre-diverter photo-eye
  input.start_pb           bool    momentary start
  input.stop_pb            bool    momentary stop
  input.reset_pb           bool    momentary reset (acknowledges + clears jam)
  input.estop              bool    emergency stop (true = engaged)
  data.parcel_destination  uint16  1 = CHUTE_A, 2 = CHUTE_B

Outputs (plc_to_sim):
  output.motor_conv_001_run      bool
  output.diverter_dv_001_extend  bool    extended => route to CHUTE_A
  alarm.jam_001                  bool    latched jam
  counter.sorted_chute_a         uint16
  counter.sorted_chute_b         uint16

Sorting model:
  - The routing decision is latched on the RISING edge of pe_002 (parcel reaches
    the diverter eye) from data.parcel_destination.
  - The counter increments on the FALLING edge of pe_002 (parcel has passed the
    diverter). A parcel that jams at pe_002 never produces a falling edge, so it
    is not counted — keeping PLC counters consistent with parcels that actually
    cleared the diverter.
"""
from __future__ import annotations

DEST_CHUTE_A = 1
DEST_CHUTE_B = 2

# Consecutive scans pe_002 may stay blocked while the motor is running before a
# jam is declared. At the Phase 1 scenario dt of 0.05 s this is ~1.0 s, well
# above a normal parcel's pe_002 dwell (~0.2 s).
JAM_SCAN_LIMIT = 20


def initial_state() -> dict:
    return {
        "running": False,
        "jam": False,
        "divert": False,
        "pending": 0,        # destination latched at the diverter eye, counted on exit
        "count_a": 0,
        "count_b": 0,
        "jam_timer": 0,
        "prev_pe_002": False,
        "prev_start": False,
        "prev_reset": False,
    }


def scan(inputs: dict, state: dict):
    pe1 = bool(inputs.get("sensor.pe_001", False))  # reserved for future infeed gating
    pe2 = bool(inputs.get("sensor.pe_002", False))
    start = bool(inputs.get("input.start_pb", False))
    stop = bool(inputs.get("input.stop_pb", False))
    reset = bool(inputs.get("input.reset_pb", False))
    estop = bool(inputs.get("input.estop", False))
    dest = int(inputs.get("data.parcel_destination", 0) or 0)

    start_edge = start and not state["prev_start"]
    reset_edge = reset and not state["prev_reset"]
    pe2_rise = pe2 and not state["prev_pe_002"]
    pe2_fall = (not pe2) and state["prev_pe_002"]

    # Reset acknowledges and clears the jam latch + any pending decision.
    if reset_edge:
        state["jam"] = False
        state["jam_timer"] = 0
        state["pending"] = 0
        state["divert"] = False

    # E-stop or Stop drop the running latch, de-energise the diverter, and void any
    # in-flight routing decision (safety: never leave the actuator latched while stopped,
    # and don't act on a stale decision after recovery).
    if estop or stop:
        state["running"] = False
        state["divert"] = False
        state["pending"] = 0

    # Start latches running only when safe.
    if start_edge and not estop and not state["jam"]:
        state["running"] = True

    motor_should_run = state["running"] and not estop and not state["jam"]

    # Jam detection: pe_002 blocked too long while the motor should be running.
    if motor_should_run and pe2:
        state["jam_timer"] += 1
    else:
        state["jam_timer"] = 0
    if state["jam_timer"] >= JAM_SCAN_LIMIT:
        state["jam"] = True
        state["running"] = False
        motor_should_run = False

    # Routing decision on the rising edge of pe_002.
    if pe2_rise and motor_should_run:
        state["pending"] = DEST_CHUTE_A if dest == DEST_CHUTE_A else DEST_CHUTE_B
        state["divert"] = (state["pending"] == DEST_CHUTE_A)

    # Count on the falling edge of pe_002 (parcel has cleared the diverter).
    if pe2_fall and motor_should_run and state["pending"]:
        if state["pending"] == DEST_CHUTE_A:
            state["count_a"] += 1
        else:
            state["count_b"] += 1
        state["pending"] = 0

    motor = motor_should_run
    divert = state["divert"] and motor

    out = {
        "output.motor_conv_001_run": motor,
        "output.diverter_dv_001_extend": divert,
        "alarm.jam_001": state["jam"],
        # uint16 counters wrap at 65536, matching the Modbus input register.
        "counter.sorted_chute_a": state["count_a"] & 0xFFFF,
        "counter.sorted_chute_b": state["count_b"] & 0xFFFF,
    }

    state["prev_pe_002"] = pe2
    state["prev_start"] = start
    state["prev_reset"] = reset
    return out, state
