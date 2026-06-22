"""OpenPLC Runtime v3 connectivity smoke test (skip-by-default).

When a live OpenPLC slave is reachable (set OPENPLC_HOST / OPENPLC_PORT), this verifies
the gateway's Modbus client can connect and exchange basic reads — proving interop with a
real PLC running the `plc/examples/*.st` programs. It SKIPS cleanly when OPENPLC_HOST is
unset, so the zero-dependency suite stays green here.

Full ST-vs-soft-PLC behavioural equivalence is a guided manual procedure (depends on your
OpenPLC I/O→Modbus address mapping); see plc/examples/README.md.

Dual-mode: `python tests/test_openplc_integration.py` (exit 0/1) or pytest.
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "protocol-gateway"))

HAVE_OPENPLC = bool(os.environ.get("OPENPLC_HOST"))


class _Skip(Exception):
    pass


def _skip_if_no_openplc():
    if HAVE_OPENPLC:
        return
    if os.environ.get("PYTEST_CURRENT_TEST"):
        import pytest
        pytest.skip("OPENPLC_HOST not set (live OpenPLC required)")
    raise _Skip()


def test_openplc_modbus_reachable():
    _skip_if_no_openplc()
    from modbus_tcp import ModbusTCPClient
    host = os.environ["OPENPLC_HOST"]
    port = int(os.environ.get("OPENPLC_PORT", "502"))
    cli = ModbusTCPClient(host, port, timeout=5.0).connect()
    try:
        # Basic reachability: the slave answers standard reads without a protocol error.
        coils = cli.read_coils(0, 8)
        di = cli.read_discrete_inputs(0, 8)
        assert isinstance(coils, list) and len(coils) == 8
        assert isinstance(di, list) and len(di) == 8
    finally:
        cli.close()


def _all_tests():
    return [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]


def main():
    passed = failed = skipped = 0
    for t in _all_tests():
        try:
            t()
            print(f"  [PASS] {t.__name__}")
            passed += 1
        except _Skip:
            print(f"  [SKIP] {t.__name__} (OPENPLC_HOST not set)")
            skipped += 1
        except AssertionError as e:
            print(f"  [FAIL] {t.__name__}: {e}")
            failed += 1
    print(f"\nOpenPLC integration: {passed} passed, {skipped} skipped, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
