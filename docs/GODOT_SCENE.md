# Godot Scene Documentation (Phase 1)

Phase 1 ships a **headless deterministic scene adapter** (`simulation/scene_model.py`)
as the authoritative plant, plus this document describing the matching Godot scene.
The Godot project visualises the same state and exchanges the same tags — it is a
view over the model, not a second source of truth.

> Why a code-side scene first: Godot can't run in CI/headless here, and Phase 1's
> acceptance criteria require *deterministic* scenarios. `scene_model.py` gives a
> reproducible plant the verification script drives. The Godot scene below is the
> visualization layer to wire next; it must read/write the same tag registry.

## Physical layout (1-D conveyor, cm)
```
   0        20            80   90            120
   |--------|-------------|----|-------------|
  infeed  pe_001        pe_002  diverter   end (CHUTE_B)
                                  |
                                  +-- spur --> CHUTE_A (diverter extended)
```
Defaults in `SceneModel`: speed 50 cm/s, parcel length 10 cm, pe_001 @20,
pe_002 @80, diverter @90, end @120.

## Proposed Godot node tree
```
SortingCell (Node3D)
├── Conveyor (MeshInstance3D + AnimatedMaterial)        # runs when output.motor_conv_001_run
├── InfeedSpawner (Node3D)                              # spawns Parcel scenes
├── PE_001 (Area3D)        -> sensor.pe_001  (bool)     # barcode scan point
├── PE_002 (Area3D)        -> sensor.pe_002  (bool)
├── Diverter (Node3D + AnimationPlayer)                 # extends on output.diverter_dv_001_extend
├── ChuteA (Area3D)                                     # counter.sorted_chute_a
├── ChuteB (Area3D)                                     # counter.sorted_chute_b
├── Stacklight (OmniLight3D)                            # alarm.jam_001 / running
└── HMIButtons (Control)  -> input.start_pb/stop_pb/reset_pb/input.estop
Parcel (RigidBody3D/CharacterBody3D)                    # carries `destination`
```

## Tag contract (Godot adapter <-> gateway)
The Godot adapter must speak exactly these tags (same as `scene_model.sensor_tags()`
and the actuator reads). See `protocol-gateway/config/tags.sorting_cell_mvp.json`
and `hmi/fuxa/tag_list_sorting_cell_mvp.csv`.

Write (scene -> PLC): `sensor.pe_001`, `sensor.pe_002`, `data.parcel_destination`,
and the HMI buttons `input.start_pb/stop_pb/reset_pb/estop`.
Read (PLC -> scene): `output.motor_conv_001_run`, `output.diverter_dv_001_extend`,
`alarm.jam_001`, `counter.sorted_chute_a`, `counter.sorted_chute_b`.

## Integration options for the Godot adapter
1. **GDExtension/GDScript Modbus client** connecting to `scripts/run_soft_plc.py`
   (the soft-PLC slave) — mirrors the Python gateway path.
2. **Bridge process**: Godot ⇄ local socket/JSON ⇄ `TagGateway`. Lowest-risk first step.

In both cases the control logic (`plc/control_logic_mvp.py` or OpenPLC) and the
tag registry are unchanged — only the *plant* swaps from `scene_model.py` to Godot.

## Determinism note
`scene_model.py` uses fixed-dt integration and no randomness, so scenarios are
reproducible (the verifier asserts a bit-identical re-run). A real-time Godot
scene is not bit-deterministic; keep `scene_model.py` as the test oracle and use
Godot for visualization / manual play.
