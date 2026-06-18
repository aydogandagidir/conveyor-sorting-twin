"""pymodbus-backed client adapter implementing the OpenLogiTwin client interface.

OPTIONAL backend: requires `pip install pymodbus`. It lets TagGateway talk to any
standard Modbus TCP slave (the in-repo soft-PLC, or a real OpenPLC) through pymodbus,
proving the gateway is transport-agnostic and that the in-repo Modbus server is
standards-compliant (a real third-party master interoperates with it).

Verified against pymodbus 3.13 (API: read_*(address, count=...) -> resp with
.bits/.registers and .isError(); write_*(address, value)). pymodbus is imported
lazily in connect(), so importing this module never requires pymodbus to be present.
"""


class PymodbusClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 15502, timeout: float = 3.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self._client = None

    def connect(self) -> "PymodbusClient":
        from pymodbus.client import ModbusTcpClient  # lazy: optional dependency
        self._client = ModbusTcpClient(self.host, port=self.port, timeout=self.timeout)
        if not self._client.connect():
            raise ConnectionError(f"pymodbus could not connect to {self.host}:{self.port}")
        return self

    def close(self):
        if self._client is not None:
            self._client.close()
            self._client = None

    def _check(self, resp):
        if resp is None or resp.isError():
            raise IOError(f"pymodbus request failed: {resp!r}")
        return resp

    def read_coils(self, address, count=1):
        return list(self._check(self._client.read_coils(address, count=count)).bits[:count])

    def read_discrete_inputs(self, address, count=1):
        return list(self._check(self._client.read_discrete_inputs(address, count=count)).bits[:count])

    def read_holding_registers(self, address, count=1):
        return list(self._check(self._client.read_holding_registers(address, count=count)).registers[:count])

    def read_input_registers(self, address, count=1):
        return list(self._check(self._client.read_input_registers(address, count=count)).registers[:count])

    def write_coil(self, address, value):
        self._check(self._client.write_coil(address, bool(value)))
        return True

    def write_register(self, address, value):
        self._check(self._client.write_register(address, int(value) & 0xFFFF))
        return True
