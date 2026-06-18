"""Pytest wrappers that run the canonical Phase 0/1 verification gates.

Keeps the standalone `verify_phase0.py` / `verify_phase1.py` scripts (CI + DoD)
while exposing them to `pytest tests/`. conftest.py puts the source dirs on sys.path.
"""
import importlib


def test_phase0_gate():
    verify_phase0 = importlib.import_module("verify_phase0")
    assert verify_phase0.main() == 0


def test_phase1_gate():
    verify_phase1 = importlib.import_module("verify_phase1")
    assert verify_phase1.main() == 0
