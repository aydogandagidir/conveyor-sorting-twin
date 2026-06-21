extends Node3D
## Visual sorting-cell plant for OpenLogiTwin.
##
## A view over the same model as simulation/scene_model.py: it connects to the soft-PLC
## through the CellBridge autoload (same tag contract), reports pe_001/pe_002 + destination,
## reads motor/diverter/jam, and moves 3-D parcels accordingly. The deterministic oracle
## stays scene_model.py — this is the visualization (docs/GODOT_SCENE.md).

const SPEED := 50.0     # cm/s   (matches SceneModel)
const PLEN := 10.0      # parcel length, cm
const PE1 := 20.0
const PE2 := 80.0
const DIVERT := 90.0
const ENDP := 120.0
const VSCALE := 0.02    # cm -> world units (120 cm -> 2.4 units)

var _parcels: Array = []
var _spawn_t := 0.0
var _next_dest := 1
var _last_dest := 0    # single-register latch: holds the last scanned destination (MVP)

func _ready() -> void:
	# Auto-start the line so the scene runs on its own (a live visual demo of the cell).
	await get_tree().create_timer(0.6).timeout      # let CellBridge connect first
	if CellBridge:
		CellBridge.press(CellBridge.START_PB, true)
		await get_tree().create_timer(0.2).timeout
		CellBridge.press(CellBridge.START_PB, false)

func _physics_process(delta: float) -> void:
	var out: Dictionary = CellBridge.read_outputs() if CellBridge else {}
	var motor := bool(out.get("motor", false))
	var diverter := bool(out.get("diverter", false))

	# auto-spawn alternating A/B parcels for a continuous demo
	_spawn_t += delta
	if _spawn_t >= 3.0:
		_spawn_t = 0.0
		_spawn_parcel(_next_dest)
		_next_dest = 2 if _next_dest == 1 else 1

	if motor:
		for p in _parcels:
			p.pos += SPEED * delta
			if not p.routed and p.pos >= DIVERT:
				p.routed = true
				p.to_a = diverter          # diverter extended -> CHUTE_A spur

	# sensor coverage (a parcel of length PLEN covers a point between tail and head)
	var pe1_cov := false
	var pe2_cov := false
	for p in _parcels:
		if p.pos - PLEN <= PE1 and PE1 <= p.pos:
			pe1_cov = true
			_last_dest = p.dest        # latch the scanned destination until pe_002
		if p.pos - PLEN <= PE2 and PE2 <= p.pos:
			pe2_cov = true
		_render(p)

	if CellBridge:
		CellBridge.write_sensors(pe1_cov, pe2_cov, _last_dest)

	var light := get_node_or_null("Stacklight")
	if light:
		light.light_energy = 4.0 if bool(out.get("jam", false)) else 0.0

	# cull parcels that have left the cell
	for p in _parcels:
		if p.pos > ENDP + 20.0 and is_instance_valid(p.node):
			p.node.queue_free()
	_parcels = _parcels.filter(func(p): return p.pos <= ENDP + 20.0)

func _spawn_parcel(dest: int) -> void:
	var mesh := MeshInstance3D.new()
	var box := BoxMesh.new()
	box.size = Vector3(PLEN * VSCALE, 0.15, 0.2)
	mesh.mesh = box
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.2, 0.6, 1.0) if dest == 1 else Color(1.0, 0.55, 0.15)
	mesh.material_override = mat
	add_child(mesh)
	_parcels.append({"pos": 0.0, "dest": dest, "routed": false, "to_a": false, "node": mesh})

func _render(p: Dictionary) -> void:
	var lateral := -0.4 if p.get("to_a", false) else 0.0
	if is_instance_valid(p.node):
		p.node.position = Vector3(p.pos * VSCALE, 0.2, lateral)
