"""Unified CLI for OpenLogiTwin — `python -m openlogitwin <command>` (or the `openlogitwin`
console script after `pip install -e .`).

A thin dispatcher over the scripts in `scripts/`: it puts the repo's source dirs on `sys.path`
(the same way each script does when run directly) and calls the target's `main()`. Run from a
clone; no install required. Unknown args after the command are passed through to the target.
"""
import importlib
import os
import sys

_PKG = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_PKG)
_SRC_DIRS = ("scripts", "protocol-gateway", "plc", "simulation", "telemetry")

# command -> (module in scripts/, passes argv through, one-line help)
COMMANDS = {
    "hmi":       ("start",            True,  "Launch the web HMI (replay + live) and open the browser"),
    "demo":      ("run_full_demo",    True,  "Run every scenario and build the demo report"),
    "scenarios": ("scenario_manager", True,  "Scenario manager: list / validate / run / run-all"),
    "export":    ("export_trace",     True,  "Export deterministic per-tick HMI traces"),
    "plc":       ("run_soft_plc",     False, "Run the soft-PLC Modbus slave standalone"),
    "test":      ("run_tests",        False, "Run the full test suite"),
}
DEFAULT = "hmi"


def _bootstrap():
    for sub in _SRC_DIRS:
        path = os.path.join(_ROOT, sub)
        if path not in sys.path:
            sys.path.insert(0, path)


def _print_help(stream=sys.stdout):
    stream.write("openlogitwin - conveyor sorting cell digital twin\n\n")
    stream.write("usage: python -m openlogitwin [command] [args...]\n\n")
    stream.write("commands (default: %s):\n" % DEFAULT)
    width = max(len(c) for c in COMMANDS)
    for name, (_mod, _argv, help_text) in COMMANDS.items():
        stream.write("  %-*s  %s\n" % (width, name, help_text))
    stream.write("\nArgs after the command pass through, e.g.  python -m openlogitwin hmi --no-browser\n")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in ("-h", "--help"):
        _print_help()
        return 0
    command, rest = DEFAULT, argv
    if argv and not argv[0].startswith("-"):
        command, rest = argv[0], argv[1:]
        if command not in COMMANDS:
            sys.stderr.write("openlogitwin: unknown command '%s'\n\n" % command)
            _print_help(sys.stderr)
            return 2
    _bootstrap()
    module_name, takes_argv, _ = COMMANDS[command]
    module = importlib.import_module(module_name)
    result = module.main(rest) if takes_argv else module.main()
    return result or 0


if __name__ == "__main__":
    sys.exit(main())
