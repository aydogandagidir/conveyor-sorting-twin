# godot-project — visualization layer (Phase 1 documented, scene to wire next)

Phase 1's authoritative plant is the headless deterministic adapter
`simulation/scene_model.py`. The Godot scene is a **view** over the same tags.

- Full scene documentation (node tree, tag contract, integration options):
  **`docs/GODOT_SCENE.md`**.
- Tag contract the Godot adapter must honour:
  `protocol-gateway/config/tags.sorting_cell_mvp.json` and `docs/TAG_MAP_MVP.md`.

## Why the Python adapter is the test oracle
Phase 1 requires *deterministic* scenarios (the verifier asserts a bit-identical
re-run). A real-time Godot scene is not bit-deterministic, so `scene_model.py`
stays the oracle for tests and Godot is used for visualization / manual play.

Run the deterministic plant today:
```bash
python scripts/run_scenario.py scenarios/barcode_sorting_basic.json
python scripts/run_scenario.py scenarios/jam_recovery_basic.json
```

## The scene (authored + verified headless on Godot 4.2)
- `project.godot` — Godot 4.2 project; main scene `cell.tscn`, autoloads `cell_bridge.gd`.
- `cell.tscn` / `cell.gd` — the 3-D sorting cell (conveyor, PE markers, chutes, stacklight) and its
  controller: spawns parcels, moves them on the motor output, routes on the diverter, and reports
  `pe_001`/`pe_002` + the scanned destination back to the PLC.
- `modbus_client.gd` — Modbus TCP client in GDScript (MBAP + FC 01–06), mirrors
  `protocol-gateway/modbus_tcp.py`.
- `cell_bridge.gd` — autoload that writes sensor/button tags and reads actuator/counter tags using
  the `tags.sorting_cell_mvp.json` addresses (drift-guarded by `tests/test_godot_project.py`).

### Run it
Start the soft-PLC, then run the scene (the line auto-starts):
```bash
OLTWIN_REGISTRY=sorting_cell_mvp OLTWIN_CONTROL=control_logic_mvp python scripts/run_soft_plc.py &
godot --path simulation/godot-project        # or open the project in the Godot 4.2 editor
```
**Verified 2026-06-20** on Godot 4.2 headless: the project imports and runs with **0 script
errors**, `CellBridge` connects to the soft-PLC, and the scene drives **real sorts over Modbus**
(both chute counters increment). Visual polish (meshes, animation) is done in the editor;
`scene_model.py` stays the deterministic test oracle.
