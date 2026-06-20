"""Client factory — selects the transport backend for TagGateway.

All backends implement the same 6-method client interface
(read_coils / read_discrete_inputs / read_holding_registers / read_input_registers /
write_coil / write_register), so the gateway, registry, scene and control logic are
unchanged regardless of transport.

kinds:
  'modbus'   in-repo Modbus TCP client (default, zero-dep)
  'local'    in-process store client (needs store=...)
  'pymodbus' pymodbus-backed client (optional: pip install pymodbus)
  'opcua'    OPC UA adapter (optional: pip install asyncua)
  'mqtt'     MQTT adapter — Phase 3 stub
"""


def make_client(kind: str = "modbus", **kwargs):
    if kind == "modbus":
        from modbus_tcp import ModbusTCPClient
        return ModbusTCPClient(**kwargs)
    if kind == "local":
        from modbus_tcp import LocalStoreClient
        return LocalStoreClient(**kwargs)
    if kind == "pymodbus":
        from adapters.pymodbus_adapter import PymodbusClient
        return PymodbusClient(**kwargs)
    if kind == "opcua":
        from adapters.opcua_adapter import OpcUaClient
        return OpcUaClient(**kwargs)
    if kind == "mqtt":
        from adapters.mqtt_stub import MqttClientStub
        return MqttClientStub(**kwargs)
    raise ValueError(f"unknown client kind: {kind!r}")
