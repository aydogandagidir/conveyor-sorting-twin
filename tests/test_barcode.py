"""Tests for the per-parcel barcode simulator (simulation/barcode.py) and its
end-to-end wiring through the scenario runner.

Covers the EAN-13 checksum, the decoder's resolution order (routes / EAN parity /
alpha prefix), and that a barcode scenario both routes correctly and emits a
`barcode_scan` telemetry event per parcel.

Dual-mode: runnable directly (`python tests/test_barcode.py`, exit 0/1) and
collectable by pytest.
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _sub in ("simulation", "scripts", "protocol-gateway", "plc", "telemetry"):
    sys.path.insert(0, os.path.join(_ROOT, _sub))

from barcode import (  # noqa: E402
    BarcodeDecoder, ean13_check_digit, is_valid_ean13, CHUTE_A, CHUTE_B,
)


def _ean13(payload12):
    return payload12 + str(ean13_check_digit(payload12))


def test_ean13_checksum_and_validation():
    code = _ean13("400638133392")
    assert is_valid_ean13(code)
    # a flipped check digit must fail
    bad = code[:12] + str((int(code[12]) + 1) % 10)
    assert not is_valid_ean13(bad)
    assert not is_valid_ean13("12345")          # wrong length
    assert not is_valid_ean13("ABCDEFGHIJKLM")   # non-numeric


def test_decoder_alpha_prefix():
    d = BarcodeDecoder()
    assert d.decode("A001") == CHUTE_A
    assert d.decode("B777") == CHUTE_B
    assert d.decode("X9") == CHUTE_A             # unknown prefix -> default A


def test_decoder_ean13_parity():
    d = BarcodeDecoder()
    assert d.decode(_ean13("400638133392")) == CHUTE_A   # last payload digit even
    assert d.decode(_ean13("400638133393")) == CHUTE_B   # last payload digit odd


def test_decoder_routes_override_wins():
    d = BarcodeDecoder(routes={"A001": "CHUTE_B", "VIP": 2})
    assert d.decode("A001") == CHUTE_B           # override beats the alpha prefix
    assert d.decode("VIP") == CHUTE_B


def test_barcode_scenario_routes_and_emits_telemetry():
    import scenario_manager
    collected = []
    path = scenario_manager.resolve("barcode_routing")
    result, _expect, mm = scenario_manager.run_and_check(
        path, use_modbus=False, telemetry_sink=collected.append)
    assert not mm                                # expectations met
    assert (result["sorted_a"], result["sorted_b"]) == (2, 1)
    scans = [e for e in collected if e["event_type"] == "barcode_scan"]
    assert len(scans) == 3
    assert {e["value"] for e in scans} == {"A001", "B002", "A003"}


def _all_tests():
    return [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]


def main():
    passed = 0
    for t in _all_tests():
        t()
        print(f"  [PASS] {t.__name__}")
        passed += 1
    print(f"barcode tests: {passed} passed, 0 failed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
