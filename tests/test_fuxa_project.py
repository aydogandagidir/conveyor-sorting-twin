"""Structure test for the generated FUXA project (Modbus device + tags).

Verifies scripts/generate_fuxa_project.py emits a structurally-valid, registry-faithful
FUXA project (1 ModbusTCP device, all 12 tags with correct Modicon addresses, deterministic
output). It does NOT verify import into a running FUXA (that's a manual step).

Dual-mode: `python tests/test_fuxa_project.py` (exit 0/1) or pytest.
"""
import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, os.path.join(_ROOT, "protocol-gateway"))

import generate_fuxa_project as gen  # noqa: E402
from tag_registry import TagRegistry  # noqa: E402


def _project():
    return json.loads(gen.as_json())


def test_single_modbus_tcp_device_with_all_tags():
    devices = _project()["projectData"]["devices"]
    assert len(devices) == 1
    dev = next(iter(devices.values()))
    assert dev["type"] == "ModbusTCP"
    assert dev["property"]["port"] == "15502"
    registry = TagRegistry.from_file(gen.REGISTRY)
    tag_names = {t["name"] for t in dev["tags"].values()}
    assert tag_names == {t.name for t in registry}, "device tags must match the registry"


def test_tag_addresses_and_access_follow_registry():
    dev = next(iter(_project()["projectData"]["devices"].values()))
    by_name = {t["name"]: t for t in dev["tags"].values()}
    # discrete-input actuator -> Modicon 1xxxxx, read-only
    motor = by_name["output.motor_conv_001_run"]
    assert motor["type"] == "Bool" and motor["address"] == "100001" and motor["access"] == "Read"
    # coil sensor -> Modicon 0xxxxx, writable by master
    pe1 = by_name["sensor.pe_001"]
    assert pe1["address"] == "000001" and pe1["access"] == "Read/Write"
    # holding-register setpoint -> 4xxxxx
    dest = by_name["data.parcel_destination"]
    assert dest["type"] == "UInt16" and dest["address"] == "400001"


def test_generation_is_deterministic():
    assert gen.as_json() == gen.as_json(), "FUXA project generation must be reproducible"


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
    print(f"\nFUXA project tests: {passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
