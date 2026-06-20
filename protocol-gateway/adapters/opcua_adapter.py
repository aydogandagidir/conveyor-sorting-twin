"""OPC UA client adapter (second protocol priority) — backed by asyncua.

OPTIONAL backend: requires `pip install asyncua`. It implements the OpenLogiTwin client
interface (read_coils / read_discrete_inputs / read_holding_registers /
read_input_registers / write_coil / write_register) on top of an OPC UA server, proving the
gateway is truly transport-agnostic — the same TagGateway/registry/control logic run over
Modbus, in-process, pymodbus, or OPC UA unchanged.

Tag coordinates `(table, address)` map to OPC UA string NodeIds `"{table}_{address}"` under a
single namespace, so the Modbus-shaped client interface maps cleanly onto OPC UA nodes.

`asyncua` is imported lazily, so importing this module never requires it to be installed.
Verified against asyncua 2.0 (sync API).
"""

OPCUA_NS = "https://openlogitwin.dev/opcua"
_TABLES = ("coil", "discrete_input", "holding_register", "input_register")
_BOOL_TABLES = ("coil", "discrete_input")


def build_opcua_server(endpoint="opc.tcp://127.0.0.1:48400/oltwin", size=16):
    """Start an in-process OPC UA server exposing the four I/O tables as writable nodes.

    Returns (server, ns_index). Stop with server.stop(). Used for tests and as an
    OPC-UA-facing stand-in for the cell I/O image.
    """
    from asyncua.sync import Server
    from asyncua import ua

    server = Server()
    server.set_endpoint(endpoint)
    ns = server.register_namespace(OPCUA_NS)
    objects = server.nodes.objects
    for table in _TABLES:
        is_bool = table in _BOOL_TABLES
        for addr in range(size):
            nodeid = ua.NodeId(f"{table}_{addr}", ns)
            if is_bool:
                var = objects.add_variable(nodeid, f"{table}_{addr}", False)
            else:
                var = objects.add_variable(nodeid, f"{table}_{addr}",
                                           ua.Variant(0, ua.VariantType.UInt16))
            var.set_writable()
    server.start()
    return server, ns


def server_set(server, ns, table, address, value):
    """Set a node value server-side (e.g. simulate a PLC output on a read-only table)."""
    from asyncua import ua
    node = server.get_node(ua.NodeId(f"{table}_{address}", ns))
    if table in _BOOL_TABLES:
        node.set_value(bool(value))
    else:
        node.set_value(ua.Variant(int(value) & 0xFFFF, ua.VariantType.UInt16))


class OpcUaClient:
    def __init__(self, endpoint="opc.tcp://127.0.0.1:48400/oltwin", timeout=4.0):
        self.endpoint = endpoint
        self.timeout = timeout
        self._client = None
        self._ns = None
        self._ua = None

    def connect(self) -> "OpcUaClient":
        from asyncua.sync import Client  # lazy: optional dependency
        from asyncua import ua
        self._ua = ua
        self._client = Client(self.endpoint, timeout=self.timeout)
        self._client.connect()
        self._ns = self._client.get_namespace_index(OPCUA_NS)
        return self

    def close(self):
        if self._client is not None:
            try:
                self._client.disconnect()
            finally:
                self._client = None

    def _node(self, table, address):
        return self._client.get_node(self._ua.NodeId(f"{table}_{address}", self._ns))

    def _read_bits(self, table, address, count):
        return [bool(self._node(table, address + i).get_value()) for i in range(count)]

    def _read_regs(self, table, address, count):
        return [int(self._node(table, address + i).get_value()) for i in range(count)]

    def read_coils(self, address, count=1):
        return self._read_bits("coil", address, count)

    def read_discrete_inputs(self, address, count=1):
        return self._read_bits("discrete_input", address, count)

    def read_holding_registers(self, address, count=1):
        return self._read_regs("holding_register", address, count)

    def read_input_registers(self, address, count=1):
        return self._read_regs("input_register", address, count)

    def write_coil(self, address, value):
        self._node("coil", address).set_value(bool(value))
        return True

    def write_register(self, address, value):
        variant = self._ua.Variant(int(value) & 0xFFFF, self._ua.VariantType.UInt16)
        self._node("holding_register", address).set_value(variant)
        return True
