"""Structural guard for the generated FUXA mimic view (no FUXA needed).

Checks that scripts/generate_fuxa_view.py produces a well-formed SVG whose bound element
ids match the binding map, and that the injected `hmi.views[0]` in the generated project
binds every readout to a REAL device tag (a drift guard tying the mimic to the registry).

Live rendering is confirmed by importing the project into FUXA (see hmi/fuxa/INTEGRATION.md);
this test keeps CI green without it. Dual-mode: direct or pytest.
"""
import json
import os
import sys
import xml.dom.minidom as minidom

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import generate_fuxa_view as G  # noqa: E402


def _text_ids(svg):
    dom = minidom.parseString(svg)
    return {e.getAttribute("id") for e in dom.getElementsByTagName("text") if e.getAttribute("id")}


def test_mimic_svg_is_wellformed_with_all_bound_ids():
    ids = _text_ids(G._mimic_svg())
    for elem_id in G.BINDINGS:
        assert elem_id in ids, f"mimic SVG missing bound element {elem_id}"


def test_committed_svg_present_and_wellformed():
    assert os.path.exists(G.SVG_OUT), "run scripts/generate_fuxa_view.py"
    with open(G.SVG_OUT, encoding="utf-8") as f:
        ids = _text_ids(f.read())
    assert set(G.BINDINGS).issubset(ids)


def test_project_view_binds_every_readout_to_a_real_tag():
    proj = json.load(open(G.PROJECT, encoding="utf-8"))
    pd = proj["projectData"]
    dev = list(pd["devices"].values())[0]
    dev_id = dev["id"]
    tags = dev["tags"]
    tag_ids = {t["id"] for t in (tags.values() if isinstance(tags, dict) else tags)}

    views = pd["hmi"].get("views", [])
    assert len(views) >= 1, "no mimic view injected — run scripts/generate_fuxa_view.py"
    view = views[0]
    assert view.get("svgcontent"), "view has no svgcontent"
    for elem_id, tag_name in G.BINDINGS.items():
        assert elem_id in view["items"], f"view missing binding {elem_id}"
        sig = view["items"][elem_id]["property"]["variableId"]
        assert sig.startswith(dev_id) and sig[len(dev_id):] in tag_ids, \
            f"{elem_id} ({tag_name}) not bound to a real device tag"


def _all_tests():
    return [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]


def main():
    passed = 0
    for t in _all_tests():
        t(); print(f"  [PASS] {t.__name__}"); passed += 1
    print(f"FUXA view tests: {passed} passed, 0 failed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
