"""OPC UA client adapter — STUB (Phase 3, second protocol priority).

Implements the OpenLogiTwin client interface shape so it drops into TagGateway and
the factory once realised, but every operation raises NotImplementedError today.

TODO (replace stub):
  - Connect to an OPC UA server (e.g. via `asyncua`).
  - Map tag names -> OPC UA NodeIds (extend the tag registry with a `nodeId`).
  - Implement read_* / write_* against the server's address space.
See adr/0002 (protocol roadmap: Modbus first, OPC UA second, MQTT third).
"""

_MSG = "OPC UA adapter is a Phase 3 stub — not implemented yet (see adr/0002 protocol roadmap)"


class OpcUaClientStub:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def connect(self):
        raise NotImplementedError(_MSG)

    def close(self):
        pass

    def read_coils(self, address, count=1):
        raise NotImplementedError(_MSG)

    def read_discrete_inputs(self, address, count=1):
        raise NotImplementedError(_MSG)

    def read_holding_registers(self, address, count=1):
        raise NotImplementedError(_MSG)

    def read_input_registers(self, address, count=1):
        raise NotImplementedError(_MSG)

    def write_coil(self, address, value):
        raise NotImplementedError(_MSG)

    def write_register(self, address, value):
        raise NotImplementedError(_MSG)
