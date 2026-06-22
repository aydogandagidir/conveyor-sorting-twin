"""Unified CLI (`python -m openlogitwin`): the front-door dispatcher must show help, reject
unknown commands, and map every command to a real script `main()`. We never invoke the `test`
command here (it would re-run the whole suite). Stdlib only. Dual-mode: direct or pytest.
"""
import importlib
import os
import subprocess
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from openlogitwin import cli  # noqa: E402


def test_help_lists_commands():
    p = subprocess.run([sys.executable, "-m", "openlogitwin", "--help"],
                       cwd=_ROOT, capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    assert "commands" in p.stdout and "hmi" in p.stdout, "help must list the commands"


def test_unknown_command_exits_nonzero():
    p = subprocess.run([sys.executable, "-m", "openlogitwin", "bogus"],
                       cwd=_ROOT, capture_output=True, text=True)
    assert p.returncode == 2, "an unknown command must fail"
    assert "unknown command" in p.stderr


def test_every_command_resolves_to_a_real_main():
    cli._bootstrap()
    for name, (module_name, _takes_argv, _help) in cli.COMMANDS.items():
        module = importlib.import_module(module_name)
        assert hasattr(module, "main") and callable(module.main), \
            f"command '{name}' -> {module_name} has no callable main()"
    assert cli.DEFAULT in cli.COMMANDS, "the default command must exist"


def _all_tests():
    return [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]


def main():
    passed = 0
    for t in _all_tests():
        t(); print(f"  [PASS] {t.__name__}"); passed += 1
    print(f"CLI tests: {passed} passed, 0 failed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
