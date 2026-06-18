"""Deterministic scenario runner for the Phase 1 MVP sorting cell.

Wires the plant, protocol and control together and steps them in fixed-dt
lock-step so a scenario is fully reproducible:

    SceneModel (plant) <-> TagGateway (Modbus master) <-> SoftPlc(control_logic_mvp)

Per tick: apply scheduled scenario events -> read scene sensors -> write tags ->
one PLC scan -> read actuator tags -> log telemetry -> advance the plant.

By default the gateway talks real Modbus TCP (proving the protocol path). Pass
use_modbus=False to use the in-process fallback. The PLC scan is driven manually
(no background thread) so ordering — and therefore the result — is deterministic.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _sub in ("protocol-gateway", "plc", "telemetry", "simulation"):
    _p = os.path.join(_ROOT, _sub)
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tag_registry import TagRegistry                 # noqa: E402
from modbus_tcp import ModbusTCPClient, LocalStoreClient  # noqa: E402
from gateway import TagGateway                        # noqa: E402
from soft_plc import SoftPlc                          # noqa: E402
from telemetry_logger import TelemetryLogger          # noqa: E402
import control_logic_mvp                              # noqa: E402
from scene_model import SceneModel, DEST_CHUTE_A, DEST_CHUTE_B  # noqa: E402

DEST_MAP = {"CHUTE_A": DEST_CHUTE_A, "CHUTE_B": DEST_CHUTE_B}
_BUTTON_DEFAULTS = {
    "input.start_pb": False,
    "input.stop_pb": False,
    "input.reset_pb": False,
    "input.estop": False,
}

VALID_ACTIONS = {"press", "release", "set_estop", "spawn_parcel", "inject_jam", "clear_jam"}


def validate_scenario(scenario) -> bool:
    """Fail-fast structural validation (stdlib only). Mirrors scenarios/schema.json.

    Raises ValueError listing every problem found.
    """
    errors = []
    if not isinstance(scenario, dict):
        raise ValueError("scenario must be a JSON object")
    if not isinstance(scenario.get("duration"), (int, float)):
        errors.append("missing or non-numeric 'duration'")
    if "dt" in scenario and not isinstance(scenario["dt"], (int, float)):
        errors.append("'dt' must be numeric")
    events = scenario.get("events")
    if not isinstance(events, list):
        errors.append("missing 'events' array")
        events = []
    for i, ev in enumerate(events):
        ctx = f"events[{i}]"
        if not isinstance(ev, dict):
            errors.append(f"{ctx}: must be an object")
            continue
        if not isinstance(ev.get("t"), (int, float)):
            errors.append(f"{ctx}: missing or non-numeric 't'")
        action = ev.get("action")
        if action not in VALID_ACTIONS:
            errors.append(f"{ctx}: invalid action {action!r} (expected one of {sorted(VALID_ACTIONS)})")
        if action in ("press", "release") and "input" not in ev:
            errors.append(f"{ctx}: '{action}' requires 'input'")
        if action == "spawn_parcel" and "destination" not in ev:
            errors.append(f"{ctx}: 'spawn_parcel' requires 'destination'")
        if action == "set_estop" and "value" not in ev:
            errors.append(f"{ctx}: 'set_estop' requires 'value'")
    if errors:
        raise ValueError("Invalid scenario:\n  - " + "\n  - ".join(errors))
    return True


class ScenarioRunner:
    def __init__(self, registry_path, telemetry_db=None, use_modbus=True):
        self.registry = TagRegistry.from_file(registry_path)
        self.plc = SoftPlc(self.registry, scan_interval=0.0, control=control_logic_mvp)
        if use_modbus:
            port = self.plc.serve("127.0.0.1", 0)
            self.client = ModbusTCPClient("127.0.0.1", port).connect()
            self.transport = f"modbus-tcp:127.0.0.1:{port}"
        else:
            self.client = LocalStoreClient(self.plc.store)
            self.transport = "local-in-process"
        self.gw = TagGateway(self.registry, self.client)
        self.telemetry_db = telemetry_db or os.path.join(
            tempfile.mkdtemp(prefix="oltwin_p1_"), "telemetry.db")
        self.tel = TelemetryLogger(self.telemetry_db, scenario="phase1")
        self.scene = None

    def run_file(self, path):
        with open(path, encoding="utf-8") as f:
            return self.run(json.load(f))

    def run(self, scenario):
        validate_scenario(scenario)  # fail fast on malformed scenarios
        dt = float(scenario.get("dt", 0.05))
        duration = float(scenario["duration"])
        self.tel.scenario = scenario.get("name", "phase1")
        self.scene = SceneModel()
        inputs = dict(_BUTTON_DEFAULTS)
        self.gw.initialize_inputs()

        events = sorted(scenario.get("events", []), key=lambda e: e["t"])
        ei = 0
        nsteps = int(round(duration / dt))
        result = {
            "name": scenario.get("name"),
            "transport": self.transport,
            "ticks": nsteps,
            "motor_on_ticks": 0,
            "sorted_a": 0,
            "sorted_b": 0,
            "destinations": [],
            "jam_triggered": False,
            "jam_cleared": False,
            "divert_on_ticks": 0,
        }
        prev_motor = None
        prev_jam = False

        for k in range(nsteps + 1):
            t = k * dt
            while ei < len(events) and events[ei]["t"] <= t + 1e-9:
                self._apply_event(events[ei], inputs, result)
                ei += 1

            stags = self.scene.sensor_tags()
            self.gw.write_tag("sensor.pe_001", stags["sensor.pe_001"])
            self.gw.write_tag("sensor.pe_002", stags["sensor.pe_002"])
            self.gw.write_tag("data.parcel_destination", stags["data.parcel_destination"])
            for name, value in inputs.items():
                self.gw.write_tag(name, value)

            self.plc.scan_once()

            motor = self.gw.read_tag("output.motor_conv_001_run")
            divert = self.gw.read_tag("output.diverter_dv_001_extend")
            jam = self.gw.read_tag("alarm.jam_001")
            ca = self.gw.read_tag("counter.sorted_chute_a")
            cb = self.gw.read_tag("counter.sorted_chute_b")

            if prev_motor is None or motor != prev_motor:
                self.tel.log_machine_state("motor_run" if motor else "motor_stop",
                                           detail=f"t={t:.2f}")
            if jam and not prev_jam:
                self.tel.log_fault("alarm.jam_001", True, detail=f"t={t:.2f}")
                result["jam_triggered"] = True
            if (not jam) and prev_jam:
                self.tel.log_fault("alarm.jam_001", False, detail=f"cleared t={t:.2f}")
                result["jam_cleared"] = True
            if ca > result["sorted_a"]:
                self.tel.log_sort("CHUTE_A", DEST_CHUTE_A, detail=f"count={ca} t={t:.2f}")
            if cb > result["sorted_b"]:
                self.tel.log_sort("CHUTE_B", DEST_CHUTE_B, detail=f"count={cb} t={t:.2f}")
            result["sorted_a"], result["sorted_b"] = ca, cb
            if motor:
                result["motor_on_ticks"] += 1
            if divert:
                result["divert_on_ticks"] += 1

            self.scene.step(dt, motor, divert)
            prev_motor, prev_jam = motor, jam

        result["scene_chute_a"] = list(self.scene.chute_a)
        result["scene_chute_b"] = list(self.scene.chute_b)
        result["telemetry_events"] = self.tel.count()
        return result

    def _apply_event(self, ev, inputs, result):
        action = ev["action"]
        if action == "press":
            inputs[ev["input"]] = True
            if ev["input"] == "input.reset_pb":
                # Operator physically clears the jam when acknowledging it.
                self.scene.clear_jam()
        elif action == "release":
            inputs[ev["input"]] = False
        elif action == "set_estop":
            inputs["input.estop"] = bool(ev["value"])
        elif action == "spawn_parcel":
            dest = DEST_MAP.get(ev["destination"], DEST_CHUTE_B)
            pid = self.scene.spawn(dest, ev.get("id"))
            result["destinations"].append([pid, ev["destination"]])
            self.tel.log_cycle("parcel_spawn", detail=f"{pid} dest={ev['destination']}")
        elif action == "inject_jam":
            pid = self.scene.inject_jam(ev.get("id"))
            self.tel.log_event("jam_inject", tag="scene", detail=f"parcel={pid}")
        elif action == "clear_jam":
            self.scene.clear_jam()
        else:
            raise ValueError(f"unknown scenario action: {action!r}")

    def close(self):
        self.tel.close()
        self.gw.close()
        self.plc.stop()
