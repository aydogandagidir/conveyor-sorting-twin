"""MQTT client adapter — STUB (Phase 3, third protocol priority / telemetry).

Implements the OpenLogiTwin client interface shape so it drops into TagGateway and
the factory once realised, but every operation raises NotImplementedError today.

TODO (replace stub):
  - Connect to an MQTT broker (e.g. via `paho-mqtt`).
  - Map tags -> topics; publish actuator/metric changes, subscribe to setpoints.
  - Note: MQTT is pub/sub, not request/response — a read_* here means "last retained
    value"; reconcile with the gateway's synchronous interface when realised.
See adr/0002 (protocol roadmap: Modbus first, OPC UA second, MQTT third).
"""

_MSG = "MQTT adapter is a Phase 3 stub — not implemented yet (see adr/0002 protocol roadmap)"


class MqttClientStub:
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
