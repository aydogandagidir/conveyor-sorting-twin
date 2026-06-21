"""Protocol gateway: translates named tags <-> Modbus addresses.

Backend-agnostic. Works with any client implementing the ModbusTCPClient
interface:
  - ModbusTCPClient  -> the Modbus TCP proof path (real sockets), and
  - LocalStoreClient -> the in-process local control fallback.

The gateway enforces Modbus master semantics: it may write only coils/holding
registers (sensors, setpoints) and read any table.
"""
from __future__ import annotations

from modbus_tcp import encode_registers, decode_registers

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
        words = reader(tag.address, tag.word_count)
        if tag.type == "bool":
            return bool(words[0])
        return decode_registers(tag.type, words)   # uint16/uint32/float32

    def write_tag(self, name: str, value):
        tag = self.registry.get(name)
        if tag.table not in _MASTER_WRITABLE:
            raise ValueError(
                f"tag {name!r} maps to {tag.table!r}, which a Modbus master cannot write"
            )
        if tag.table == "coil":
            self.client.write_coil(tag.address, bool(value))
            return
        for offset, word in enumerate(encode_registers(tag.type, value)):
            self.client.write_register(tag.address + offset, word)

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
