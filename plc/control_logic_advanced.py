"""Advanced control: per-parcel destination via a FIFO ring (Phase 1.5f prototype).

Removes the single-shared-destination limitation of control_logic_mvp.py.
Destinations are delivered through a ring of holding registers
(`data.dest_ring_0..RING_SIZE-1`): the plant writes each parcel's destination as it
is scanned at pe_001 (enqueue), and the PLC dequeues on the pe_002 rising edge.
A single-lane conveyor is strictly FIFO (no overtaking), so dequeue order matches
enqueue order regardless of how many parcels are buffered between pe_001 and pe_002.

Same (initial_state, scan) contract as control_logic_mvp.py — plugs into SoftPlc via
the `control` parameter. Still a STUB for OpenPLC. See adr/0005.
"""
from __future__ import annotations

DEST_CHUTE_A = 1
DEST_CHUTE_B = 2
JAM_SCAN_LIMIT = 20
RING_SIZE = 8


def initial_state() -> dict:
    return {
        "running": False, "jam": False, "divert": False, "pending": 0,
        "count_a": 0, "count_b": 0, "jam_timer": 0,
        "prev_pe_002": False, "prev_start": False, "prev_reset": False,
        "read_idx": 0,
    }


def scan(inputs: dict, state: dict):
    pe2 = bool(inputs.get("sensor.pe_002", False))
    start = bool(inputs.get("input.start_pb", False))
    stop = bool(inputs.get("input.stop_pb", False))
    reset = bool(inputs.get("input.reset_pb", False))
    estop = bool(inputs.get("input.estop", False))

    start_edge = start and not state["prev_start"]
    reset_edge = reset and not state["prev_reset"]
    pe2_rise = pe2 and not state["prev_pe_002"]
    pe2_fall = (not pe2) and state["prev_pe_002"]

    if reset_edge:
        state["jam"] = False
        state["jam_timer"] = 0
        state["pending"] = 0
        state["divert"] = False

    if estop or stop:
        state["running"] = False
        state["divert"] = False

    if start_edge and not estop and not state["jam"]:
        state["running"] = True

    motor_should_run = state["running"] and not estop and not state["jam"]

    if motor_should_run and pe2:
        state["jam_timer"] += 1
    else:
        state["jam_timer"] = 0
    if state["jam_timer"] >= JAM_SCAN_LIMIT:
        state["jam"] = True
        state["running"] = False
        motor_should_run = False

    # Dequeue this parcel's destination from the FIFO ring on the rising edge.
    if pe2_rise and motor_should_run:
        slot = state["read_idx"] % RING_SIZE
        dest = int(inputs.get(f"data.dest_ring_{slot}", 0) or 0)
        state["read_idx"] += 1
        state["pending"] = DEST_CHUTE_A if dest == DEST_CHUTE_A else DEST_CHUTE_B
        state["divert"] = (state["pending"] == DEST_CHUTE_A)

    # Count on the falling edge (parcel cleared the diverter).
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
        "counter.sorted_chute_a": state["count_a"],
        "counter.sorted_chute_b": state["count_b"],
    }
    state["prev_pe_002"] = pe2
    state["prev_start"] = start
    state["prev_reset"] = reset
    return out, state
