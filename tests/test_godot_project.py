"""Structural guard for the Godot visualization project (no Godot needed).

The Godot scene is a *view* over the same model as scene_model.py and must speak the
same tag contract. This checks the project is wired up (main scene set, .tscn references
the controller script, key nodes present) and — the important part — that the
`cell_bridge.gd` Modbus address constants stay in lock-step with the tag registry.

Full runtime validation is done with Godot headless (see simulation/godot-project/README.md);
this test keeps CI green without Godot. Dual-mode: direct or pytest.
"""
import json
import os
import re
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GP = os.path.join(_ROOT, "simulation", "godot-project")
REGISTRY = os.path.join(_ROOT, "protocol-gateway", "config", "tags.sorting_cell_mvp.json")

# cell_bridge.gd constant -> registry tag it must address.
CONST_TO_TAG = {
    "PE_001": "sensor.pe_001", "PE_002": "sensor.pe_002",
    "START_PB": "input.start_pb", "STOP_PB": "input.stop_pb",
    "RESET_PB": "input.reset_pb", "ESTOP": "input.estop",
    "DEST": "data.parcel_destination",
    "MOTOR": "output.motor_conv_001_run", "DIVERTER": "output.diverter_dv_001_extend",
    "JAM": "alarm.jam_001",
    "COUNT_A": "counter.sorted_chute_a", "COUNT_B": "counter.sorted_chute_b",
}


def _read(name):
    with open(os.path.join(GP, name), encoding="utf-8") as f:
        return f.read()


def test_project_files_present():
    for name in ("project.godot", "cell.tscn", "cell.gd", "cell_bridge.gd", "modbus_client.gd"):
        assert os.path.exists(os.path.join(GP, name)), f"missing {name}"


def test_main_scene_and_autoload_wired():
    proj = _read("project.godot")
    assert 'run/main_scene="res://cell.tscn"' in proj, "main scene not set to cell.tscn"
    assert 'CellBridge="*res://cell_bridge.gd"' in proj, "CellBridge autoload missing"


def test_scene_references_controller_and_key_nodes():
    tscn = _read("cell.tscn")
    assert 'path="res://cell.gd"' in tscn, "cell.tscn does not reference cell.gd"
    for node in ('name="SortingCell"', 'name="Conveyor"', 'name="PE_001"', 'name="PE_002"',
                 'name="ChuteA"', 'name="ChuteB"'):
        assert node in tscn, f"cell.tscn missing node {node}"


def test_bridge_addresses_match_registry():
    bridge = _read("cell_bridge.gd")
    consts = {m.group(1): int(m.group(2))
              for m in re.finditer(r"const (\w+)\s*:=\s*(\d+)", bridge)}
    tags = json.load(open(REGISTRY, encoding="utf-8"))["tags"]
    addr = {t["name"]: t["modbus"]["address"] for t in tags}
    for const, tag in CONST_TO_TAG.items():
        assert const in consts, f"cell_bridge.gd missing const {const}"
        assert consts[const] == addr[tag], \
            f"{const}={consts[const]} but registry {tag} is at address {addr[tag]}"


def _all_tests():
    return [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]


def main():
    passed = 0
    for t in _all_tests():
        t(); print(f"  [PASS] {t.__name__}"); passed += 1
    print(f"godot project tests: {passed} passed, 0 failed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
