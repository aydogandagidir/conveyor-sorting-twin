"""Generate a FUXA mimic view (SVG + live tag bindings) for the sorting cell.

Reads the device/tags from the generated FUXA project and produces:
  - hmi/fuxa/mimic_sorting_cell.svg     — a stand-alone SVG mimic of the cell
  - injects an `hmi.views[0]` into hmi/fuxa/openlogitwin_project.json, binding the
    dynamic readouts (motor, diverter, jam, counters) to the device's tags so FUXA
    shows them live (svg-ext-value gauges).

Pairs with INTEGRATION.md: import the project into FUXA and the mimic is already drawn
and bound — no manual editor work to see live values. Stdlib only.

Usage: python scripts/generate_fuxa_view.py
"""
import json
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT = os.path.join(_ROOT, "hmi", "fuxa", "openlogitwin_project.json")
SVG_OUT = os.path.join(_ROOT, "hmi", "fuxa", "mimic_sorting_cell.svg")

# SVG element id -> registry tag name (the live readouts)
BINDINGS = {
    "val_motor": "output.motor_conv_001_run",
    "val_diverter": "output.diverter_dv_001_extend",
    "val_jam": "alarm.jam_001",
    "val_count_a": "counter.sorted_chute_a",
    "val_count_b": "counter.sorted_chute_b",
}

W, H = 760, 340


def _mimic_svg():
    """A self-contained dark-theme mimic: conveyor, PE eyes, diverter, two chutes, readouts."""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <rect x="0" y="0" width="{W}" height="{H}" fill="#0d1117"/>
  <text x="24" y="34" fill="#e6edf3" font-family="Segoe UI,Arial" font-size="20" font-weight="700">OpenLogiTwin — Sorting Cell</text>
  <text x="24" y="56" fill="#9198a1" font-family="Segoe UI,Arial" font-size="12">live mimic (FUXA / Modbus)</text>

  <!-- conveyor belt -->
  <rect x="60" y="150" width="520" height="40" rx="6" fill="#21262d" stroke="#30363d"/>
  <text x="60" y="210" fill="#6e7681" font-family="Arial" font-size="11">infeed</text>

  <!-- photo-eyes -->
  <circle cx="160" cy="170" r="6" fill="#2f81f7"/><text x="146" y="138" fill="#9198a1" font-family="Arial" font-size="11">PE_001</text>
  <circle cx="460" cy="170" r="6" fill="#2f81f7"/><text x="446" y="138" fill="#9198a1" font-family="Arial" font-size="11">PE_002</text>

  <!-- diverter + chutes -->
  <rect x="500" y="120" width="14" height="50" rx="3" fill="#d29922"/>
  <rect x="600" y="90"  width="120" height="44" rx="6" fill="#132a1a" stroke="#3fb950"/>
  <text x="612" y="116" fill="#3fb950" font-family="Arial" font-size="13">CHUTE A</text>
  <rect x="600" y="186" width="120" height="44" rx="6" fill="#2a1a13" stroke="#f0883e"/>
  <text x="612" y="212" fill="#f0883e" font-family="Arial" font-size="13">CHUTE B</text>

  <!-- live readouts (bound by FUXA to the device tags) -->
  <g font-family="Consolas,monospace" font-size="15">
    <text x="80"  y="280" fill="#9198a1" font-size="12">MOTOR</text>
    <text id="val_motor"    x="80"  y="300" fill="#3fb950">0</text>
    <text x="200" y="280" fill="#9198a1" font-size="12">DIVERTER</text>
    <text id="val_diverter" x="200" y="300" fill="#d29922">0</text>
    <text x="330" y="280" fill="#9198a1" font-size="12">JAM</text>
    <text id="val_jam"      x="330" y="300" fill="#f85149">0</text>
    <text x="450" y="280" fill="#9198a1" font-size="12">COUNT A</text>
    <text id="val_count_a"  x="450" y="300" fill="#3fb950">0</text>
    <text x="590" y="280" fill="#9198a1" font-size="12">COUNT B</text>
    <text id="val_count_b"  x="590" y="300" fill="#f0883e">0</text>
  </g>
</svg>"""


def main():
    proj = json.load(open(PROJECT, encoding="utf-8"))
    pd = proj["projectData"]
    device = list(pd["devices"].values())[0]
    dev_id = device["id"]
    tags = device["tags"]
    tag_items = list(tags.values()) if isinstance(tags, dict) else tags
    id_by_name = {t["name"]: t["id"] for t in tag_items}

    svg = _mimic_svg()
    with open(SVG_OUT, "w", encoding="utf-8") as f:
        f.write(svg)

    # one svg-ext-value gauge per dynamic element, bound to its tag's signal id
    items = {}
    for elem_id, tag_name in BINDINGS.items():
        signal_id = dev_id + id_by_name[tag_name]      # FUXA signal id = deviceId + tagId
        items[elem_id] = {
            "id": elem_id,
            "type": "svg-ext-value",
            "name": tag_name,
            "property": {"variableId": signal_id, "permission": 0},
        }

    view = {
        "id": "view_mimic",
        "name": "SortingCell",
        "profile": {"width": W, "height": H, "bkcolor": "#0d1117", "margin": 10},
        "svgcontent": svg,
        "items": items,
        "variables": [],
    }
    pd["hmi"]["views"] = [view]
    pd["hmi"].setdefault("layout", {"navigation": {"type": "", "menu": {}}})
    with open(PROJECT, "w", encoding="utf-8") as f:
        json.dump(proj, f, indent=2)

    print(f"wrote {os.path.relpath(SVG_OUT, _ROOT)} and injected hmi.views[0] "
          f"({len(items)} bound readouts) into {os.path.relpath(PROJECT, _ROOT)}")


if __name__ == "__main__":
    main()
