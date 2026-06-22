"""Structural guard for the web HMI — split into index.html / hmi.css / hmi.js.

Keeps the HMI wired up and High-Performance-HMI (ISA-101) compliant: the engine loads
traces and ticks via setInterval (background/kiosk safe); the markup exposes the controls,
the mimic, and the ISA-18.2 alarm summary; and the stylesheet stays free of the gradients
and drop-shadows the research flags as amateurish. Runtime behaviour is verified separately
in a real browser. Dual-mode: direct or pytest.
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HMI = os.path.join(_ROOT, "web", "hmi")
LANDING = os.path.join(_ROOT, "web", "index.html")
PAGES_WF = os.path.join(_ROOT, ".github", "workflows", "pages.yml")


def _read(*p):
    with open(os.path.join(*p), encoding="utf-8") as f:
        return f.read()


def test_split_files_present():
    for name in ("index.html", "hmi.css", "hmi.js"):
        assert os.path.exists(os.path.join(HMI, name)), f"web/hmi/{name} missing"


def test_index_links_assets_and_exposes_components():
    html = _read(HMI, "index.html")
    assert html.lstrip().lower().startswith("<!doctype html>")
    assert 'href="hmi.css"' in html and 'src="hmi.js"' in html, "index must link hmi.css + hmi.js"
    for needed in ('id="scenario"', 'id="play"', 'id="seek"', 'id="speed"', 'id="cell"',
                   'id="alm-rows"', 'id="banner"', 'id="st-motor"', 'id="b-ack"'):
        assert needed in html, f"index.html missing {needed}"


def test_faceplate_and_alarm_rationalisation_present():
    html = _read(HMI, "index.html")
    assert 'id="fp-ov"' in html and 'id="fp-body"' in html, "faceplate overlay missing"
    js = _read(HMI, "hmi.js")
    # ISA-18.2 rationalisation fields (cause / consequence / corrective action) + the opener
    assert "openFp" in js and "Corrective action" in js, "alarm rationalisation faceplate missing"


def test_display_hierarchy_and_theme_present():
    html = _read(HMI, "index.html")
    assert 'id="lv1"' in html and 'id="lv3"' in html, "level navigation chips missing"
    assert 'id="view-line"' in html and 'id="view-io"' in html, "L1/L3 views missing"
    assert 'id="theme"' in html, "theme toggle missing"
    js = _read(HMI, "hmi.js")
    assert "setLevel" in js and "data-theme" in js, "nav/theme logic missing"


def test_engine_loads_traces_and_is_interval_driven():
    js = _read(HMI, "hmi.js")
    assert "traces/index.json" in js and 'fetch("traces/' in js, "engine must load traces"
    assert "setInterval(tick" in js, "engine must tick via setInterval (background/kiosk safe)"
    assert "sv-parcels" in js, "engine must render parcels"


def test_live_mode_present():
    html = _read(HMI, "index.html")
    assert 'id="go-live"' in html and 'id="b-jam"' in html, "live-mode controls missing"
    js = _read(HMI, "hmi.js")
    assert "WebSocket" in js and "liveFrame" in js and "sendCmd" in js, "live-mode client missing"
    # not just that the names exist — the button must be wired and the process controls must
    # route to live commands when connected (guards against a dead/unwired live client).
    assert '$("go-live").onclick' in js, "Go-live button is not wired to a handler"
    assert "if (liveMode) return sendCmd(" in js, "process buttons must send live commands in LIVE mode"


def test_estop_is_priority_one_alarm():
    # ISA-18.2: an E-stop is the most critical event — it must be a P1 alarm, in both the
    # replay button path and the live-frame edge handler (parity).
    js = _read(HMI, "hmi.js")
    assert 'addAlarm(1, "CELL-01"' in js, "E-stop must raise a priority-1 CELL-01 alarm"
    assert 'addAlarm(2, "CELL-01"' not in js, "E-stop must not be a P2 alarm"


def test_css_is_high_performance_hmi_compliant():
    css = _read(HMI, "hmi.css")
    # HP-HMI palette tokens present (colour reserved for data + alarms)
    for tok in ("--data", "--band", "--p1", "--p2", "--p3", "--on", "--off"):
        assert tok in css, f"hmi.css missing token {tok}"
    # the amateurish anti-patterns the research flags must be absent (check real usage,
    # not the word in a comment): no gradient functions, no drop shadows.
    low = css.lower()
    for grad in ("linear-gradient", "radial-gradient", "conic-gradient"):
        assert grad not in low, "HP-HMI forbids gradients"
    assert "box-shadow:" not in low, "HP-HMI forbids drop shadows"
    assert "tabular-nums" in css, "numeric values must use tabular figures"


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
