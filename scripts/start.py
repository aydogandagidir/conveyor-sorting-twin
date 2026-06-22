"""One-command launcher for OpenLogiTwin (V5).

Starts everything a new user needs to see the twin in a browser, in one command:
  - exports the demo traces if they're missing (so replay works offline),
  - serves the web HMI over HTTP,
  - (optionally) starts the live WebSocket server so the HMI's "Go live" button drives the
    real soft-PLC,
  - opens the browser at the HMI.

Stdlib only — no third-party packages. Ctrl-C to stop.

Usage:
  python scripts/start.py                      # export (if needed) + serve + live + open browser
  python scripts/start.py --no-live            # replay only (no WebSocket server)
  python scripts/start.py --no-browser --port 9000
"""
import argparse
import functools
import os
import sys
import threading
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(_ROOT, "web")
TRACES_INDEX = os.path.join(WEB_DIR, "hmi", "traces", "index.json")
WS_PORT = 8765   # the HMI client connects to ws://<host>:8765 (see web/hmi/hmi.js)
sys.path.insert(0, os.path.join(_ROOT, "scripts"))


class _QuietHandler(SimpleHTTPRequestHandler):
    """SimpleHTTPRequestHandler without the per-request stderr logging."""
    def log_message(self, *args):
        pass


def ensure_traces():
    """Export the curated demo traces if they haven't been generated yet. Returns True if it
    actually exported (False if they already existed)."""
    if os.path.exists(TRACES_INDEX):
        return False
    import export_trace
    export_trace.main([])
    return True


def build_static_server(host, port):
    """An HTTP server rooted at web/, so `/hmi/` serves the HMI. Pass port 0 for an ephemeral
    port (the caller reads server_address[1])."""
    handler = functools.partial(_QuietHandler, directory=WEB_DIR)
    return ThreadingHTTPServer((host, port), handler)


def start_live_server(host, ws_port=WS_PORT):
    """Start the live twin WebSocket server in the background. Returns (server, bound_port)."""
    from hmi_server import HmiServer, TwinEngine
    srv = HmiServer(TwinEngine(), host, ws_port)
    return srv, srv.serve()


def run(host="127.0.0.1", port=8099, live=True, open_browser=True):
    exported = ensure_traces()
    httpd = build_static_server(host, port)
    port = httpd.server_address[1]
    shown_host = "localhost" if host in ("127.0.0.1", "0.0.0.0") else host
    url = "http://%s:%d/hmi/" % (shown_host, port)

    live_srv = None
    if live:
        try:
            live_srv, _ = start_live_server(host)
        except OSError as exc:
            print("  ! live server could not bind :%d (%s) — continuing in replay only" % (WS_PORT, exc))

    print("OpenLogiTwin")
    if exported:
        print("  exported demo traces -> web/hmi/traces/")
    print("  HMI:   %s" % url)
    if live_srv:
        print("  live:  ws://%s:%d  (click 'Go live' in the HMI)" % (shown_host, WS_PORT))
    else:
        print("  mode:  replay only")
    print("  Ctrl-C to stop.")

    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopping...")
    finally:
        httpd.shutdown()
        httpd.server_close()
        if live_srv:
            live_srv.stop()


def main(argv=None):
    ap = argparse.ArgumentParser(description="Launch the OpenLogiTwin web HMI (replay + live).")
    ap.add_argument("--host", default="127.0.0.1", help="bind host (default 127.0.0.1)")
    ap.add_argument("--port", type=int, default=8099, help="HTTP port for the HMI (default 8099)")
    ap.add_argument("--no-live", action="store_true", help="replay only; don't start the WebSocket server")
    ap.add_argument("--no-browser", action="store_true", help="don't open a browser; just print the URL")
    args = ap.parse_args(argv)
    run(host=args.host, port=args.port, live=not args.no_live, open_browser=not args.no_browser)
    return 0


if __name__ == "__main__":
    sys.exit(main())
