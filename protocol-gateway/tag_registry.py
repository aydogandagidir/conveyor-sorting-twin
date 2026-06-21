"""Tag registry: load + validate the tag mapping, expose Tag objects.

The registry is the single source of truth that maps human-readable tag names
(e.g. "sensor.preDivert") to Modbus addresses and to a data-flow direction.

A formal JSON Schema lives at protocol-gateway/schema/tag_registry.schema.json
for IDE/tooling use. This module additionally performs structural validation in
pure Python so the project has zero third-party dependencies for Phase 0.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

VALID_TABLES = {"coil", "discrete_input", "holding_register", "input_register"}
VALID_TYPES = {"bool", "uint16", "uint32", "float32"}
VALID_DIRECTIONS = {"sim_to_plc", "plc_to_sim"}

# Modbus master semantics: a master may WRITE coils/holding_registers and only
# READ discrete_inputs/input_registers. Sensors (sim->plc) must therefore live
# in master-writable tables; actuators (plc->sim) in master-readable tables.
MASTER_WRITABLE_TABLES = {"coil", "holding_register"}
MASTER_READONLY_TABLES = {"discrete_input", "input_register"}


@dataclass(frozen=True)
class Tag:
    name: str
    type: str
    direction: str
    role: str
    table: str
    address: int
    description: str = ""
    initial: Any = None
    invert: bool = False  # bool tags only: PLC-side I/O conditioning (e.g. NC fail-safe E-stop)

    def default_value(self):
        if self.initial is not None:
            return self.initial
        if self.type == "bool":
            return False
        return 0.0 if self.type == "float32" else 0

    @property
    def word_count(self) -> int:
        """16-bit registers this tag occupies (2 for uint32/float32, else 1)."""
        return 2 if self.type in ("uint32", "float32") else 1


class TagRegistry:
    def __init__(self, tags, meta=None):
        self.tags = {t.name: t for t in tags}
        self.meta = meta or {}

    @classmethod
    def from_dict(cls, data: dict) -> "TagRegistry":
        validate_registry(data)
        tags = []
        for t in data["tags"]:
            tags.append(
                Tag(
                    name=t["name"],
                    type=t["type"],
                    direction=t["direction"],
                    role=t.get("role", ""),
                    table=t["modbus"]["table"],
                    address=int(t["modbus"]["address"]),
                    description=t.get("description", ""),
                    initial=t.get("initial"),
                    invert=bool(t.get("invert", False)),
                )
            )
        meta = {k: v for k, v in data.items() if k != "tags"}
        return cls(tags, meta)

    @classmethod
    def from_file(cls, path: str) -> "TagRegistry":
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))

    def get(self, name: str) -> Tag:
        return self.tags[name]

    def by_direction(self, direction: str):
        return [t for t in self.tags.values() if t.direction == direction]

    def sim_to_plc(self):
        return self.by_direction("sim_to_plc")

    def plc_to_sim(self):
        return self.by_direction("plc_to_sim")

    def __len__(self):
        return len(self.tags)

    def __iter__(self):
        return iter(self.tags.values())


def validate_registry(data: dict) -> bool:
    """Structural validation. Raises ValueError listing every problem found."""
    errors = []
    if not isinstance(data, dict):
        raise ValueError("tag registry must be a JSON object")
    if "tags" not in data or not isinstance(data["tags"], list) or not data["tags"]:
        errors.append("missing non-empty 'tags' array")

    seen_names = set()
    seen_addresses = set()
    for i, t in enumerate(data.get("tags", [])):
        ctx = f"tags[{i}]"
        if not isinstance(t, dict):
            errors.append(f"{ctx}: must be an object")
            continue
        for req in ("name", "type", "direction", "modbus"):
            if req not in t:
                errors.append(f"{ctx}: missing required field '{req}'")
        if t.get("type") not in VALID_TYPES:
            errors.append(f"{ctx}: invalid type {t.get('type')!r} (expected one of {sorted(VALID_TYPES)})")
        if t.get("direction") not in VALID_DIRECTIONS:
            errors.append(f"{ctx}: invalid direction {t.get('direction')!r}")

        modbus = t.get("modbus", {})
        table = modbus.get("table")
        address = modbus.get("address")
        if table not in VALID_TABLES:
            errors.append(f"{ctx}: invalid modbus.table {table!r}")
        if not isinstance(address, int) or address < 0:
            errors.append(f"{ctx}: modbus.address must be a non-negative integer")

        name = t.get("name")
        if name in seen_names:
            errors.append(f"{ctx}: duplicate tag name {name!r}")
        seen_names.add(name)

        key = (table, address)
        if key in seen_addresses:
            errors.append(f"{ctx}: duplicate modbus address {key}")
        seen_addresses.add(key)

        # Direction / table consistency against Modbus master semantics.
        direction = t.get("direction")
        if direction == "sim_to_plc" and table not in MASTER_WRITABLE_TABLES:
            errors.append(
                f"{ctx}: sim_to_plc tag {name!r} must use a master-writable table "
                f"(coil/holding_register), got {table!r}"
            )
        if direction == "plc_to_sim" and table not in MASTER_READONLY_TABLES:
            errors.append(
                f"{ctx}: plc_to_sim tag {name!r} must use a master-readable table "
                f"(discrete_input/input_register), got {table!r}"
            )

    if errors:
        raise ValueError("Invalid tag registry:\n  - " + "\n  - ".join(errors))
    return True
