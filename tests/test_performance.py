"""Throughput / performance baseline for the advanced (FIFO-ring) sorting cell.

Runs a dense 100-parcel stream through the deterministic runner and asserts:
  - every parcel is routed and the A/B split is exact (no drops, no mis-routes),
  - the run is deterministic (identical results across two runs),
  - it completes well within a generous wall-clock budget.

The measured baseline is recorded in docs/PERFORMANCE.md. Wall-clock uses time.perf_counter;
the bound is deliberately very generous (≫ the sub-second baseline) so a loaded shared CI runner
never flakes — it trips only on a pathological (orders-of-magnitude) regression.

Dual-mode: runnable directly (`python tests/test_performance.py`, exit 0/1) and
collectable by pytest.
"""
import os
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _sub in ("simulation", "plc", "protocol-gateway", "telemetry"):
    sys.path.insert(0, os.path.join(_ROOT, _sub))

from scenario_runner import ScenarioRunner  # noqa: E402
import control_logic_advanced               # noqa: E402

ADV_REGISTRY = os.path.join(_ROOT, "protocol-gateway", "config", "tags.sorting_cell_advanced.json")


def _build_dense(n=100, spacing=0.4):
    """A dense alternating A/B stream on the advanced cell."""
    events = [
        {"t": 0.0, "action": "press",   "input": "input.start_pb"},
        {"t": 0.1, "action": "release", "input": "input.start_pb"},
    ]
    for i in range(n):
        dest = "CHUTE_A" if i % 2 == 0 else "CHUTE_B"
        events.append({"t": round(0.5 + i * spacing, 3), "action": "spawn_parcel",
                       "id": f"P{i}", "destination": dest})
    duration = round(0.5 + n * spacing + 3.0, 3)
    return {"name": "perf_dense", "cell": "sorting_cell_advanced", "dt": 0.05,
            "duration": duration, "events": events}


def _run(scenario):
    runner = ScenarioRunner(ADV_REGISTRY, use_modbus=False,
                            control=control_logic_advanced, dest_strategy="fifo_ring")
    try:
        return runner.run(scenario)
    finally:
        runner.close()


def test_throughput_100_parcels_all_routed():
    sc = _build_dense(100, 0.4)
    t0 = time.perf_counter()
    r = _run(sc)
    elapsed = time.perf_counter() - t0
    assert r["sorted_a"] + r["sorted_b"] == 100, r
    assert r["sorted_a"] == 50 and r["sorted_b"] == 50, r
    assert elapsed < 60.0, f"too slow: {elapsed:.2f}s"   # ≫ sub-second baseline; catches only a pathological regression
    print(f"  100 parcels: A/B={r['sorted_a']}/{r['sorted_b']} in {elapsed * 1000:.0f} ms "
          f"({r['ticks']} ticks, {r['ticks'] / elapsed:,.0f} ticks/s)")


def test_run_is_deterministic():
    sc = _build_dense(60, 0.4)
    a = _run(sc)
    b = _run(sc)
    assert (a["sorted_a"], a["sorted_b"], a["destinations"]) == \
           (b["sorted_a"], b["sorted_b"], b["destinations"])


def _all_tests():
    return [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]


def main():
    passed = 0
    for t in _all_tests():
        t()
        print(f"  [PASS] {t.__name__}")
        passed += 1
    print(f"performance tests: {passed} passed, 0 failed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
