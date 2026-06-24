"""Build customization for a self-contained wheel.

OpenLogiTwin's runtime lives in the repo's flat, partly-hyphenated source dirs
(`protocol-gateway/`, `plc/`, `simulation/`, `telemetry/`, `scripts/`, `web/`, `scenarios/`),
imported via per-module `sys.path` bootstraps — it was built to be cloned and run, not imported
as a library. Rather than restructure ~40 files, we **bundle** those dirs into
`openlogitwin/_bundled/` at build time. Because every module resolves its paths relative to its
own `__file__`, the bundled tree mirrors the repo exactly, so configs / web assets / scenarios all
resolve unchanged. At runtime `openlogitwin.cli._bootstrap()` prefers `_bundled/` when present
(an installed wheel) and falls back to the repo dirs (a clone / editable install).

Metadata lives in pyproject.toml; this file only adds the build-time vendoring step.
"""
import os
import shutil

from setuptools import setup
from setuptools.command.build_py import build_py

_ROOT = os.path.dirname(os.path.abspath(__file__))

_VENDOR = ["scripts", "protocol-gateway", "plc", "simulation", "telemetry", "scenarios", "web", "tests"]
_SKIP_DIRS = {"__pycache__", ".pytest_cache", "traces", "exports", ".godot", "export"}
_SKIP_EXT = (".pyc", ".pyo", ".db", ".sqlite", ".sqlite3")


def _ignore(_src, names):
    return [n for n in names if n in _SKIP_DIRS or n.endswith(_SKIP_EXT)]


class _VendorBuildPy(build_py):
    """Copy the runtime source dirs into openlogitwin/_bundled/ in the built package."""

    def run(self):
        super().run()
        bundled = os.path.join(self.build_lib, "openlogitwin", "_bundled")
        for sub in _VENDOR:
            src = os.path.join(_ROOT, sub)
            if not os.path.isdir(src):
                continue
            dst = os.path.join(bundled, sub)
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst, ignore=_ignore)


setup(cmdclass={"build_py": _VendorBuildPy})
