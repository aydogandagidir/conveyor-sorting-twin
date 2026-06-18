# Minimal Modbus TCP client for Godot 4.x — mirrors protocol-gateway/modbus_tcp.py.
# Lets the Godot scene read/write the soft-PLC (or real OpenPLC) tags.
#
# STATUS: best-effort scaffold; verify in Godot 4.x. Implements MBAP framing +
# FC 01/02/03/04/05/06 (the subset the cell needs).
extends RefCounted
class_name ModbusTcpClient

var _peer := StreamPeerTCP.new()
var _txn := 0

func connect_to_plc(host: String, port: int, timeout_ms := 3000) -> bool:
	var err := _peer.connect_to_host(host, port)
	if err != OK:
		return false
	var deadline := Time.get_ticks_msec() + timeout_ms
	while Time.get_ticks_msec() < deadline:
		_peer.poll()
		if _peer.get_status() == StreamPeerTCP.STATUS_CONNECTED:
			return true
		OS.delay_msec(5)
	return false

func close() -> void:
	_peer.disconnect_from_host()

func _be16(value: int) -> PackedByteArray:
	return PackedByteArray([(value >> 8) & 0xFF, value & 0xFF])

func _request(function: int, data: PackedByteArray) -> PackedByteArray:
	_txn = (_txn + 1) & 0xFFFF
	var body := PackedByteArray([1, function])  # unit id 1 + function code
	body.append_array(data)
	var adu := _be16(_txn)
	adu.append_array(_be16(0))            # protocol id
	adu.append_array(_be16(body.size()))  # length
	adu.append_array(body)
	_peer.put_data(adu)
	# read 6-byte MBAP header then the declared length
	var header := _recv(6)
	var length := (header[4] << 8) | header[5]
	var rest := _recv(length)
	var fc := rest[1]
	if fc & 0x80:
		push_error("Modbus exception fc=%d code=%d" % [fc & 0x7F, rest[2]])
		return PackedByteArray()
	return rest.slice(2)  # data after unit id + function code

func _recv(n: int) -> PackedByteArray:
	var buf := PackedByteArray()
	while buf.size() < n:
		_peer.poll()
		var avail := _peer.get_available_bytes()
		if avail > 0:
			var res := _peer.get_data(min(avail, n - buf.size()))
			if res[0] == OK:
				buf.append_array(res[1])
		else:
			OS.delay_msec(1)
	return buf

func _unpack_bits(raw: PackedByteArray, count: int) -> Array:
	var bits := []
	for i in range(count):
		bits.append(bool((raw[1 + (i >> 3)] >> (i & 7)) & 1))  # raw[0] is byte count
	return bits

func read_coils(address: int, count := 1) -> Array:
	var d := _be16(address); d.append_array(_be16(count))
	return _unpack_bits(_request(0x01, d), count)

func read_discrete_inputs(address: int, count := 1) -> Array:
	var d := _be16(address); d.append_array(_be16(count))
	return _unpack_bits(_request(0x02, d), count)

func _read_registers(fc: int, address: int, count: int) -> Array:
	var d := _be16(address); d.append_array(_be16(count))
	var resp := _request(fc, d)
	var regs := []
	for i in range(count):
		regs.append((resp[1 + i * 2] << 8) | resp[2 + i * 2])  # resp[0] is byte count
	return regs

func read_holding_registers(address: int, count := 1) -> Array:
	return _read_registers(0x03, address, count)

func read_input_registers(address: int, count := 1) -> Array:
	return _read_registers(0x04, address, count)

func write_coil(address: int, value: bool) -> void:
	var d := _be16(address); d.append_array(_be16(0xFF00 if value else 0x0000))
	_request(0x05, d)

func write_register(address: int, value: int) -> void:
	var d := _be16(address); d.append_array(_be16(value & 0xFFFF))
	_request(0x06, d)
