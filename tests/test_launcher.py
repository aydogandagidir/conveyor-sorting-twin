"""V5 launcher (`scripts/start.py`): the one-command entry point must serve the web HMI and the
traces it fetches. We exercise the testable units (trace export + static server) over a real HTTP
request on an ephemeral port — without blocking on serve_forever or opening a browser. Stdlib only.
Dual-mode: direct or pytest.
"""
import os
import sys
import threading
import urllib.request

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import start  # noqa: E402


def _get(port, path):
    with urllib.request.urlopen("http://127.0.0.1:%d%s" % (port, path), timeout=5) as r:
        return r.status, r.read().decode("utf-8", "replace")


def test_static_server_serves_the_hmi_and_traces():
    start.ensure_traces()                      # make sure the HMI has traces to load
    httpd = start.build_static_server("127.0.0.1", 0)
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    try:
        status, body = _get(port, "/hmi/")
        assert status == 200, "HMI did not serve"
        assert "OpenLogiTwin" in body and 'src="hmi.js"' in body, "served page is not the HMI"
        # the manifest the HMI fetches must be served from the same root
        status2, manifest = _get(port, "/hmi/traces/index.json")
        assert status2 == 200 and '"traces"' in manifest, "traces manifest not served"
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_launcher_exposes_cli_and_constants():
    # the launcher must expose its entry points and target the WS port the HMI client uses
    for attr in ("main", "run", "ensure_traces", "build_static_server", "start_live_server"):
        assert hasattr(start, attr), f"start.py missing {attr}"
    assert start.WS_PORT == 8765, "launcher WS port must match the HMI client (ws://host:8765)"


def _all_tests():
    return [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]


def main():
    passed = 0
    for t in _all_tests():
        t(); print(f"  [PASS] {t.__name__}"); passed += 1
    print(f"launcher tests: {passed} passed, 0 failed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
