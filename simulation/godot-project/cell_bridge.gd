# Autoload bridge: connects the Godot scene (plant) to the soft-PLC over Modbus TCP.
# The scene's physics writes sensor/button tags and reads actuator/counter tags, using
# the same addresses as protocol-gateway/config/tags.sorting_cell_mvp.json — so the Godot
# scene is a drop-in visual replacement for simulation/scene_model.py.
#
# STATUS: best-effort scaffold; verify in Godot 4.x. Start the PLC first:
#   python scripts/run_soft_plc.py   (OLTWIN_REGISTRY=sorting_cell_mvp OLTWIN_CONTROL=control_logic_mvp)
extends Node

const HOST := "127.0.0.1"
const PORT := 15502

# coils (sim -> plc)
const PE_001 := 0
const PE_002 := 1
const START_PB := 2
const STOP_PB := 3
const RESET_PB := 4
const ESTOP := 5
# holding register (sim -> plc)
const DEST := 0
# discrete inputs (plc -> sim)
const MOTOR := 0
const DIVERTER := 1
const JAM := 2
# input registers (plc -> sim)
const COUNT_A := 0
const COUNT_B := 1

# preload (not the global class_name) so the autoload resolves on a fresh headless import too
const ModbusClientScript := preload("res://modbus_client.gd")
var _client
var connected := false

func _ready() -> void:
	_client = ModbusClientScript.new()
	connected = _client.connect_to_plc(HOST, PORT)
	if not connected:
		push_warning("CellBridge: soft-PLC not reachable at %s:%d — run scripts/run_soft_plc.py" % [HOST, PORT])

# Called each physics frame by the scene with the current sensor state.
func write_sensors(pe1: bool, pe2: bool, destination: int) -> void:
	if not connected:
		return
	_client.write_coil(PE_001, pe1)
	_client.write_coil(PE_002, pe2)
	_client.write_register(DEST, destination)

func press(button_coil: int, down: bool) -> void:
	if connected:
		_client.write_coil(button_coil, down)

# Returns the PLC outputs the scene should render this frame.
func read_outputs() -> Dictionary:
	if not connected:
		return {}
	var di = _client.read_discrete_inputs(MOTOR, 3)
	var regs = _client.read_input_registers(COUNT_A, 2)
	return {
		"motor": di[0],
		"diverter": di[1],
		"jam": di[2],
		"count_a": regs[0],
		"count_b": regs[1],
	}
