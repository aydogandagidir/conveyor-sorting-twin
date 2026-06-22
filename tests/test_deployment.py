"""Deployment drift guard: the turnkey `demo` profile must run the web-HMI launcher and publish
the HMI + live-WS ports, and the image must copy the repo (the launcher needs web/ + scripts/ +
the source dirs). Text-based — the repo is stdlib-only, so no PyYAML. Dual-mode: direct or pytest.
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMPOSE = os.path.join(_ROOT, "deployment", "docker-compose.yml")
DOCKERFILE = os.path.join(_ROOT, "deployment", "Dockerfile")


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def test_demo_profile_runs_the_web_hmi_launcher():
    c = _read(COMPOSE)
    assert "web-hmi:" in c, "web-hmi service missing from the compose stack"
    assert '"demo"' in c, "the turnkey 'demo' profile is missing"
    # the service must launch via the unified CLI (V5.2), not an ad-hoc command
    assert '"openlogitwin", "hmi"' in c, "web-hmi must run `python -m openlogitwin hmi`"
    assert "--host" in c and "0.0.0.0" in c, "the HMI must bind 0.0.0.0 inside the container"


def test_demo_publishes_hmi_and_ws_ports():
    c = _read(COMPOSE)
    assert ":8099" in c, "the web HMI HTTP port (8099) must be published"
    assert "8765:8765" in c, "the live WebSocket port must be fixed at 8765 (the HMI client hardcodes it)"


def test_image_copies_the_repo_for_the_launcher():
    d = _read(DOCKERFILE)
    assert "COPY . /app" in d, "the launcher needs web/ + scripts/ + source dirs copied into the image"
    di = os.path.join(_ROOT, ".dockerignore")
    if os.path.exists(di):
        ignore = _read(di)
        assert "web/" not in ignore.split(), ".dockerignore must not exclude web/ (the HMI assets)"


def _all_tests():
    return [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]


def main():
    passed = 0
    for t in _all_tests():
        t(); print(f"  [PASS] {t.__name__}"); passed += 1
    print(f"deployment tests: {passed} passed, 0 failed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
