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

## Phase 3 scaffold (best-effort — verify in Godot 4.x)
- `project.godot` — minimal Godot 4.x project (autoloads `cell_bridge.gd`).
- `modbus_client.gd` — Modbus TCP client in GDScript (MBAP + FC 01–06), mirrors
  `protocol-gateway/modbus_tcp.py`.
- `cell_bridge.gd` — autoload that writes sensor/button tags and reads actuator/counter
  tags using the `tags.sorting_cell_mvp.json` addresses.

These are **scaffolds**: open the project in Godot 4.x, build the scene per
`docs/GODOT_SCENE.md`, and wire its physics to `CellBridge.write_sensors(...)` /
`CellBridge.read_outputs()`. The `.tscn` scene is authored in the editor (not committed).
Start the PLC first: `OLTWIN_REGISTRY=sorting_cell_mvp OLTWIN_CONTROL=control_logic_mvp python scripts/run_soft_plc.py`.
