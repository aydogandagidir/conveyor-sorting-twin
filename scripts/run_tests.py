"""Run the full OpenLogiTwin test suite (stdlib only — no pytest required).

Each test script is run as an isolated subprocess. Exit 0 only if all pass.
This is the canonical command CI uses; `pytest tests/` is an equivalent runner
when pytest is installed.

Usage: python scripts/run_tests.py
"""
import os
import subprocess
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SUITE = [
    "tests/verify_phase0.py",            # Phase 0 connectivity gate (19)
    "tests/verify_phase1.py",            # Phase 1 MVP gate (14, incl. Phase 0 regression)
    "tests/test_control_logic_mvp.py",   # control logic unit tests
    "tests/test_estop_failsafe.py",      # NC fail-safe E-stop
    "tests/test_scenario_schema.py",     # scenario validation
    "tests/test_modbus_protocol.py",     # Modbus FC + exception paths
    "tests/test_multi_parcel_prototype.py",  # multi-parcel FIFO prototype
    "tests/test_phase2_scenarios.py",    # Phase 2 scenario suite (faults + controls)
    "tests/test_pymodbus_adapter.py",    # protocol factory + pymodbus adapter (skips w/o pymodbus)
    "tests/test_opcua_adapter.py",       # OPC UA adapter (skips w/o asyncua)
    "tests/test_hmi_tag_list.py",        # FUXA tag list drift guard
    "tests/test_demo_report.py",         # Phase 3c demo runner + report generator
    "tests/test_st_examples.py",         # Phase 3b OpenPLC ST structural lint
    "tests/test_openplc_integration.py", # Phase 3b OpenPLC connectivity (skips w/o OPENPLC_HOST)
    "tests/test_fuxa_project.py",        # Phase 2/3 generated FUXA project structure
    "tests/test_advanced_cell.py",       # multi-parcel FIFO cell promoted (ADR-0005)
]


def main():
    failed = []
    for rel in SUITE:
        path = os.path.join(_ROOT, rel)
        proc = subprocess.run([sys.executable, path], cwd=_ROOT)
        status = "PASS" if proc.returncode == 0 else "FAIL"
        print(f"{status}  {rel}")
        if proc.returncode != 0:
            failed.append(rel)
    print("=" * 56)
    if failed:
        print("SUITE FAILED: " + ", ".join(failed))
        return 1
    print(f"SUITE GREEN: {len(SUITE)} test files passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
