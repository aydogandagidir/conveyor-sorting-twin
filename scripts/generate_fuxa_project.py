"""Generate a FUXA project JSON (Modbus TCP device + tags) from the tag registry.

Grounded in FUXA's data model (Device / DeviceNetProperty / Tag / Hmi / View — taken from
the FUXA source). The device and its 12 tags are derived from
protocol-gateway/config/tags.sorting_cell_mvp.json so they never drift. GUIDs are
deterministic (uuid5) for reproducible output.

STATUS: best-effort, NOT verified in a running FUXA instance here. Import it into FUXA to
confirm; type/access strings and the top-level envelope may need tweaking for your FUXA
version. The mimic SVG screens are best drawn in the FUXA editor (see hmi/fuxa/INTEGRATION.md).

Usage:
  python scripts/generate_fuxa_project.py            # write hmi/fuxa/openlogitwin_project.json
"""
import json
import os
import sys
import uuid

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "protocol-gateway"))

from tag_registry import TagRegistry  # noqa: E402

REGISTRY = os.path.join(_ROOT, "protocol-gateway", "config", "tags.sorting_cell_mvp.json")
OUT_PATH = os.path.join(_ROOT, "hmi", "fuxa", "openlogitwin_project.json")

_NS = uuid.uuid5(uuid.NAMESPACE_URL, "openlogitwin.fuxa")
_TYPE = {"bool": "Bool", "uint16": "UInt16"}
_MODICON_BASE = {"coil": 1, "discrete_input": 100001, "holding_register": 400001, "input_register": 300001}


def _uid(kind, name):
    return "f" + uuid.uuid5(_NS, f"{kind}:{name}").hex[:16]


def build_project(registry):
    device_id = _uid("device", "OpenLogiTwin-PLC")
    tags = {}
    for t in registry:
        tid = _uid("tag", t.name)
        tags[tid] = {
            "id": tid,
            "name": t.name,
            "type": _TYPE.get(t.type, "Int"),
            "address": f"{_MODICON_BASE[t.table] + t.address:06d}",  # Modicon reference
            "memaddress": str(t.address),                            # 0-based offset
            "access": "Read/Write" if t.direction == "sim_to_plc" else "Read",
            "description": t.description,
            "init": "",
            "value": "",
        }

    device = {
        "id": device_id,
        "name": "OpenLogiTwin-PLC",
        "enabled": True,
        "type": "ModbusTCP",
        "polling": 1000,
        "property": {
            "address": "127.0.0.1",
            "port": "15502",
            "slaveid": "1",
            "options": "",
        },
        "tags": tags,
    }

    view = {
        "id": _uid("view", "control_panel"),
        "name": "Control Panel",
        "type": "svg",
        "profile": {"width": 800, "height": 600, "bkcolor": "#0f172a", "margin": 10},
        "items": {},          # widgets authored in the FUXA editor (bind to the tags above)
        "variables": {},
        "svgcontent": "",
        "property": {},
    }

    return {
        "version": "1.1.0",
        "projectData": {
            "version": "1.1.0",
            "hmi": {"layout": {}, "views": [view]},
            "devices": {device_id: device},
            "texts": [],
            "charts": [],
        },
    }


def as_json(registry=None):
    registry = registry or TagRegistry.from_file(REGISTRY)
    return json.dumps(build_project(registry), indent=2, sort_keys=True)


def main():
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(as_json())
    print(f"wrote {os.path.relpath(OUT_PATH, _ROOT)} (1 ModbusTCP device, "
          f"{len(TagRegistry.from_file(REGISTRY))} tags)")
    print("NOTE: best-effort FUXA model; import into FUXA to verify (mimic screens drawn there).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
