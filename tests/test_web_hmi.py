"""Structural guard for the web HMI (web/hmi/index.html) — no browser needed.

Keeps the HMI wired up: it must load traces, expose the player controls, render the cell,
and stay tick-driven by setInterval (so it runs in background/kiosk tabs, not only when the
page is visible). Also checks the Pages workflow publishes it and the landing links to it.
Runtime behaviour is verified separately in a real browser. Dual-mode: direct or pytest.
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HMI = os.path.join(_ROOT, "web", "hmi", "index.html")
LANDING = os.path.join(_ROOT, "web", "index.html")
PAGES_WF = os.path.join(_ROOT, ".github", "workflows", "pages.yml")


def _read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def test_hmi_exists_and_loads_traces():
    assert os.path.exists(HMI), "web/hmi/index.html is missing"
    html = _read(HMI)
    assert html.lstrip().lower().startswith("<!doctype html>")
    assert "traces/index.json" in html, "HMI must load the trace manifest"
    assert 'fetch("traces/' in html, "HMI must fetch per-scenario traces"


def test_hmi_has_player_controls_and_cell():
    html = _read(HMI)
    for needed in ('id="scenario"', 'id="play"', 'id="seek"', 'id="speed"',
                   'id="cell"', 'sv-parcels', 'id="log"'):
        assert needed in html, f"HMI missing {needed}"


def test_hmi_is_interval_driven_not_only_raf():
    # setInterval keeps the animation alive in hidden/background tabs; rAF alone freezes there.
    html = _read(HMI)
    assert "setInterval(tick" in html, "HMI must tick via setInterval"


def test_pages_publishes_hmi_and_landing_links_it():
    wf = _read(PAGES_WF)
    assert "export_trace.py" in wf and "_site/hmi" in wf, "pages.yml must build the HMI"
    assert 'href="hmi/"' in _read(LANDING), "landing must link to the HMI"


def _all_tests():
    return [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]


def main():
    passed = 0
    for t in _all_tests():
        t(); print(f"  [PASS] {t.__name__}"); passed += 1
    print(f"web HMI tests: {passed} passed, 0 failed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
