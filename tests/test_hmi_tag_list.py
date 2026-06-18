"""Drift guard: the FUXA tag list must match the tag registry.

The CSV is generated from protocol-gateway/config/tags.sorting_cell_mvp.json by
scripts/generate_hmi_tag_list.py. This test fails if the committed CSV is stale.

Dual-mode: `python tests/test_hmi_tag_list.py` (exit 0/1) or pytest.
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, os.path.join(_ROOT, "protocol-gateway"))

import generate_hmi_tag_list as gen  # noqa: E402


def test_fuxa_tag_list_matches_registry():
    current = open(gen.CSV_PATH, encoding="utf-8").read()
    assert current == gen.as_string(), (
        "hmi/fuxa/tag_list_sorting_cell_mvp.csv drifted from the registry; "
        "run `python scripts/generate_hmi_tag_list.py`")


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
    print(f"\nHMI tag list tests: {passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
