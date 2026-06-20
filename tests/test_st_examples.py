"""Structural lint for the sample OpenPLC Structured Text programs.

There is no ST compiler in this repo, so this checks the example .st files are present,
well-formed (PROGRAM/END_PROGRAM, VAR blocks), and contain the expected IEC 61131-3
constructs and I/O addresses. It guards against truncation/obvious breakage; full
compilation must still be done in the OpenPLC editor (see plc/examples/README.md).

Dual-mode: `python tests/test_st_examples.py` (exit 0/1) or pytest.
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLES = os.path.join(_ROOT, "plc", "examples")


def _read(name):
    with open(os.path.join(EXAMPLES, name), encoding="utf-8") as f:
        return f.read()


def test_both_examples_present_and_wellformed():
    for name in ("01_basic_conveyor_latch.st", "02_sorting_cell_mvp.st"):
        src = _read(name)
        assert src.strip(), f"{name} is empty"
        assert src.count("END_PROGRAM") == 1, f"{name}: expected exactly one END_PROGRAM"
        assert "PROGRAM " in src, f"{name}: missing PROGRAM header"
        assert src.rstrip().endswith(("END_PROGRAM", "END_CONFIGURATION")), \
            f"{name}: truncated (no trailing END_PROGRAM/END_CONFIGURATION)"
        assert "VAR" in src and "END_VAR" in src, f"{name}: missing VAR block"


def test_sorting_cell_has_expected_constructs():
    src = _read("02_sorting_cell_mvp.st")
    required = [
        "R_TRIG", "F_TRIG", "TON", "T#1s",
        "%IX0.0", "%IX0.5", "%IW0", "%QX0.0", "%QW0", "%QW1",
        "estop_engaged", "pe2_rise", "pe2_fall", "jam_timer",
        "count_a := count_a + 1", "count_b := count_b + 1",
    ]
    missing = [tok for tok in required if tok not in src]
    assert not missing, f"02_sorting_cell_mvp.st missing constructs: {missing}"
    assert src.count("END_IF") >= 5, "expected several IF/END_IF blocks"


def test_basic_latch_has_estop_failsafe_inversion():
    src = _read("01_basic_conveyor_latch.st")
    assert "estop_engaged := NOT estop_in" in src, "missing NC fail-safe inversion (ADR-0004)"
    assert "motor := running AND NOT estop_engaged" in src


def _all_tests():
    return [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]


def main():
    passed = failed = 0
    for t in _all_tests():
        try:
            t()
            print(f"  [PASS] {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  [FAIL] {t.__name__}: {e}")
            failed += 1
    print(f"\nST example tests: {passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
