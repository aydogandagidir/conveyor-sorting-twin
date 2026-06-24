"""Packaging guard for the self-contained wheel (V5.5).

`setup.py` vendors the runtime source dirs into `openlogitwin/_bundled/` at build time, and
`openlogitwin.cli._bootstrap()` prefers that bundled copy when installed (a clone / editable
install falls back to the repo dirs). We don't build a wheel here — that's verified at release
time / by `PUBLISHING.md`; this guards the config so the build can't silently rot. Stdlib only.
Dual-mode: direct or pytest.
"""
import importlib
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from openlogitwin import cli  # noqa: E402


def _read(*p):
    with open(os.path.join(_ROOT, *p), encoding="utf-8") as f:
        return f.read()


def test_setup_vendors_the_runtime_dirs():
    setup = _read("setup.py")
    assert "build_py" in setup and "_bundled" in setup, "setup.py must bundle into _bundled via build_py"
    # every source dir the CLI bootstraps must be vendored, plus the assets the runtime loads
    for d in ("scripts", "protocol-gateway", "plc", "simulation", "telemetry", "scenarios", "web"):
        assert d in setup, f"setup.py must vendor the {d}/ dir into the wheel"


def test_cli_bootstrap_prefers_bundled_and_resolves_all_commands():
    src = _read("openlogitwin", "cli.py")
    assert "_bundled" in src, "cli._bootstrap must prefer the bundled runtime when installed"
    # from a clone (no _bundled) it must still put every command's module on the path
    cli._bootstrap()
    for name, (module_name, _takes_argv, _help) in cli.COMMANDS.items():
        importlib.import_module(module_name)


def test_pyproject_is_build_and_console_script_ready():
    pp = _read("pyproject.toml")
    assert "[build-system]" in pp and "setuptools.build_meta" in pp, "pyproject needs a build-system"
    assert "[project.scripts]" in pp and "openlogitwin.cli:main" in pp, "the openlogitwin console script must be declared"


def _all_tests():
    return [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]


def main():
    passed = 0
    for t in _all_tests():
        t(); print(f"  [PASS] {t.__name__}"); passed += 1
    print(f"packaging tests: {passed} passed, 0 failed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
