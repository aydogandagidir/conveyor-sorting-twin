"""Deterministic 1-D conveyor sorting cell plant model (Phase 1 scene adapter).

This is the authoritative, headless simulation 'scene' for Phase 1: a fixed-step
physical model that the control logic acts on through the tag registry. It is the
code-side twin of the Godot scene documented in docs/GODOT_SCENE.md — the Godot
project visualises exactly this state and reports the same sensor/actuator tags.

Physical model (1-D conveyor, position in cm, parcel leading edge = pos):

    0        20            80   90            120
    |--------|-------------|----|-------------|
   infeed  pe_001        pe_002  diverter   end(CHUTE_B)
                                   |
                                   +-- spur --> CHUTE_A (when diverter extended)

- Parcels enter at pos 0 and move +x at `speed` when the motor runs.
- A photo-eye at sx is blocked while a parcel spans it: pos-length <= sx <= pos.
- The barcode is "read" when a parcel's leading edge first passes pe_001; the
  scene then publishes data.parcel_destination for the control logic.
- At the diverter, a parcel routes to CHUTE_A if the diverter is extended, else
  it continues to CHUTE_B. Routed parcels leave the line.
- A jam is injected by sticking a parcel in place; it keeps its photo-eye blocked
  until the operator clears it on reset.

No wall-clock, no randomness: identical inputs always produce identical output.
"""
from __future__ import annotations

DEST_CHUTE_A = 1
DEST_CHUTE_B = 2


class Parcel:
    __slots__ = ("id", "destination", "pos", "scanned", "stuck", "routed_to")

    def __init__(self, pid, destination, pos=0.0):
        self.id = pid
        self.destination = destination
        self.pos = pos
        self.scanned = False
        self.stuck = False
        self.routed_to = None


class SceneModel:
    def __init__(self, speed=50.0, length=10.0,
                 pe1_x=20.0, pe2_x=80.0, divert_x=90.0, end_x=120.0):
        self.speed = speed
        self.plen = length
        self.pe1_x = pe1_x
        self.pe2_x = pe2_x
        self.divert_x = divert_x
        self.end_x = end_x
        self.parcels = []
        self.published_destination = 0
        self.chute_a = []
        self.chute_b = []
        self.events = []
        self._spawn_seq = 0

    # --- mutation API driven by the scenario --------------------------------
    def spawn(self, destination, pid=None):
        if pid is None:
            self._spawn_seq += 1
            pid = f"P{self._spawn_seq}"
        self.parcels.append(Parcel(pid, destination, pos=0.0))
        return pid

    def inject_jam(self, pid=None):
        target = None
        if pid is not None:
            target = next((p for p in self.parcels if p.id == pid), None)
        if target is None and self.parcels:
            target = max(self.parcels, key=lambda p: p.pos)
        if target is not None:
            target.stuck = True
            return target.id
        return None

    def clear_jam(self):
        """Operator clears stuck parcels (on reset)."""
        removed = [p.id for p in self.parcels if p.stuck]
        if removed:
            self.parcels = [p for p in self.parcels if not p.stuck]
        return removed

    # --- sensing -------------------------------------------------------------
    def sensor_blocked(self, sx):
        for p in self.parcels:
            if (p.pos - self.plen) <= sx <= p.pos:
                return True
        return False

    def sensor_tags(self):
        return {
            "sensor.pe_001": self.sensor_blocked(self.pe1_x),
            "sensor.pe_002": self.sensor_blocked(self.pe2_x),
            "data.parcel_destination": self.published_destination,
        }

    # --- physics step --------------------------------------------------------
    def step(self, dt, motor_on, divert_extend):
        """Advance the plant one tick given the latest actuator outputs."""
        self.events = []

        if motor_on:
            for p in self.parcels:
                if not p.stuck:
                    p.pos += self.speed * dt

        # Barcode scan at pe_001 (publish destination on first crossing).
        for p in self.parcels:
            if not p.scanned and p.pos >= self.pe1_x:
                p.scanned = True
                self.published_destination = p.destination
                self.events.append(("scan", p.id, p.destination))

        # Routing at the diverter; routed parcels leave the line.
        remaining = []
        for p in self.parcels:
            if p.routed_to is None and p.pos >= self.divert_x:
                if divert_extend:
                    p.routed_to = "A"
                    self.chute_a.append(p.id)
                else:
                    p.routed_to = "B"
                    self.chute_b.append(p.id)
                self.events.append(("routed", p.id, p.routed_to))
            else:
                remaining.append(p)
        self.parcels = remaining
        return self.events
