"""Protocol gateway: translates named tags <-> Modbus addresses.

Backend-agnostic. Works with any client implementing the ModbusTCPClient
interface:
  - ModbusTCPClient  -> the Modbus TCP proof path (real sockets), and
  - LocalStoreClient -> the in-process local control fallback.

The gateway enforces Modbus master semantics: it may write only coils/holding
registers (sensors, setpoints) and read any table.
"""
from __future__ import annotations

_READERS = {
    "coil": "read_coils",
    "discrete_input": "read_discrete_inputs",
    "holding_register": "read_holding_registers",
    "input_register": "read_input_registers",
}
_MASTER_WRITABLE = {"coil", "holding_register"}


class TagGateway:
    def __init__(self, registry, client):
        self.registry = registry
        self.client = client

    def connect(self) -> "TagGateway":
        self.client.connect()
        return self

    def close(self):
        self.client.close()

    def read_tag(self, name: str):
        tag = self.registry.get(name)
        reader = getattr(self.client, _READERS[tag.table])
        raw = reader(tag.address, 1)[0]
        return bool(raw) if tag.type == "bool" else int(raw)

    def write_tag(self, name: str, value):
        tag = self.registry.get(name)
        if tag.table not in _MASTER_WRITABLE:
            raise ValueError(
                f"tag {name!r} maps to {tag.table!r}, which a Modbus master cannot write"
            )
        if tag.table == "coil":
            self.client.write_coil(tag.address, bool(value))
        else:
            self.client.write_register(tag.address, int(value))

    def read_many(self, names=None) -> dict:
        if names is None:
            names = [t.name for t in self.registry.plc_to_sim()]
        return {n: self.read_tag(n) for n in names}

    def write_many(self, values: dict):
        for name, value in values.items():
            self.write_tag(name, value)

    def initialize_inputs(self):
        """Write every sim_to_plc tag to its declared initial value."""
        for tag in self.registry.sim_to_plc():
            self.write_tag(tag.name, tag.default_value())

    def snapshot(self) -> dict:
        return {t.name: self.read_tag(t.name) for t in self.registry}
