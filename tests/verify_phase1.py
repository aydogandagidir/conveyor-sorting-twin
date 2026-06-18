"""Phase 1 verification — proves the MVP conveyor sorting cell acceptance criteria.

Runs two deterministic scenarios through the full stack
(SceneModel <-> Modbus gateway <-> soft-PLC(control_logic_mvp)) and asserts:

  - User can run a deterministic scenario (re-run is bit-identical).
  - Parcels are assigned destinations.
  - Diverter output changes based on destination.
  - Chute counters increment.
  - Jam fault can be triggered and reset.
  - Telemetry records cycle, sorting and fault events.

Run:  python tests/verify_phase1.py     (exit 0 = all checks pass)
"""
from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _sub in ("protocol-gateway", "plc", "telemetry", "simulation"):
    sys.path.insert(0, os.path.join(_ROOT, _sub))

from scenario_runner import ScenarioRunner  # noqa: E402

REGISTRY = os.path.join(_ROOT, "protocol-gateway", "config", "tags.sorting_cell_mvp.json")
SCEN_DIR = os.path.join(_ROOT, "scenarios")
BASIC = os.path.join(SCEN_DIR, "barcode_sorting_basic.json")
JAM = os.path.join(SCEN_DIR, "jam_recovery_basic.json")

_checks = []


class CheckFailure(Exception):
    pass


def check(label, condition, detail=""):
    ok = bool(condition)
    _checks.append((label, ok))
    suffix = f"  ({detail})" if detail else ""
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}{suffix}")
    if not ok:
        raise CheckFailure(label + (f": {detail}" if detail else ""))


def _telemetry_event_types(db_path):
    import sqlite3
    conn = sqlite3.connect(db_path)
    rows = conn.execute("SELECT DISTINCT event_type FROM events").fetchall()
    conn.close()
    return {r[0] for r in rows}


def run_basic():
    print("\n[1/3] barcode_sorting_basic — sorting + counters + determinism")
    r = ScenarioRunner(REGISTRY)
    res = r.run_file(BASIC)
    db = r.telemetry_db
    r.close()

    check("scenario ran to completion", res["ticks"] > 0 and res["motor_on_ticks"] > 0,
          f"{res['motor_on_ticks']}/{res['ticks']} motor-on ticks")
    check("4 parcels assigned destinations",
          [d[1] for d in res["destinations"]] == ["CHUTE_A", "CHUTE_B", "CHUTE_A", "CHUTE_B"],
          str(res["destinations"]))
    check("chute A counter == 2", res["sorted_a"] == 2, f"A={res['sorted_a']}")
    check("chute B counter == 2", res["sorted_b"] == 2, f"B={res['sorted_b']}")
    check("diverter changed based on destination (extended for A only)",
          res["divert_on_ticks"] > 0 and res["sorted_a"] == 2 and res["sorted_b"] == 2,
          f"divert_on_ticks={res['divert_on_ticks']}")
    check("scene physically routed 2->A and 2->B",
          len(res["scene_chute_a"]) == 2 and len(res["scene_chute_b"]) == 2,
          f"A={res['scene_chute_a']} B={res['scene_chute_b']}")

    types = _telemetry_event_types(db)
    check("telemetry has cycle + sort + machine_state events",
          {"cycle", "sort", "machine_state"} <= types, str(sorted(types)))

    # Determinism: a second identical run must produce identical results.
    r2 = ScenarioRunner(REGISTRY)
    res2 = r2.run_file(BASIC)
    r2.close()
    comparable = {k: v for k, v in res.items() if k != "transport"}
    comparable2 = {k: v for k, v in res2.items() if k != "transport"}
    check("re-run is deterministic (identical result)", comparable == comparable2,
          "results differ" if comparable != comparable2 else "")


def run_jam():
    print("\n[2/3] jam_recovery_basic — jam trigger + reset + recovery")
    r = ScenarioRunner(REGISTRY)
    res = r.run_file(JAM)
    db = r.telemetry_db
    r.close()

    check("jam fault triggered", res["jam_triggered"] is True)
    check("jam fault cleared on reset", res["jam_cleared"] is True)
    check("motor stopped during jam then resumed", res["motor_on_ticks"] < res["ticks"],
          f"{res['motor_on_ticks']}/{res['ticks']} motor-on ticks")
    check("jammed parcel not counted, recovery parcel sorted to B",
          res["sorted_a"] == 0 and res["sorted_b"] == 1,
          f"A={res['sorted_a']} B={res['sorted_b']}")

    types = _telemetry_event_types(db)
    check("telemetry recorded fault events", "fault" in types, str(sorted(types)))


def run_phase0_regression():
    print("\n[3/3] Phase 0 regression (must still pass)")
    import subprocess
    p = subprocess.run([sys.executable, os.path.join(_ROOT, "tests", "verify_phase0.py")],
                       capture_output=True, text=True)
    ok = p.returncode == 0 and "19/19" in p.stdout
    check("Phase 0 verification still passes", ok,
          (p.stdout.strip().splitlines() or ["<no output>"])[-1])


def main() -> int:
    print("=" * 66)
    print("OpenLogiTwin - Phase 1 Verification (MVP Sorting Cell)")
    print("=" * 66)
    try:
        run_basic()
        run_jam()
        run_phase0_regression()
    except CheckFailure as e:
        print(f"\nRESULT: FAIL - {e}")
        return 1
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        print(f"\nRESULT: FAIL - unexpected error: {e}")
        return 1
    passed = sum(1 for _, ok in _checks if ok)
    print("\n" + "=" * 66)
    print(f"RESULT: PASS - {passed}/{len(_checks)} checks passed")
    print("=" * 66)
    return 0


if __name__ == "__main__":
    sys.exit(main())
