# Performance & Throughput

OpenLogiTwin's runner is a **deterministic, fixed-`dt` lock-step** simulator — it is built for
reproducibility, not wall-clock speed. Even so, the in-process path is fast enough to run dense
streams far quicker than real time, which is what makes the scenario suite and CI cheap.

This page records a baseline so regressions are visible. Numbers are **machine-dependent and
indicative** — the guard test (`tests/test_performance.py`) asserts *correctness + determinism*
strictly and wall-clock only against a generous ceiling, so CI never flakes on a slow runner.

## What is measured
- **Cell:** advanced (FIFO-ring, `sorting_cell_advanced`) — the profile built for dense streams.
- **Load:** 100 parcels, alternating A/B, spaced 0.4 s; `dt = 0.05 s`.
- **Transport:** in-process (`LocalStoreClient`) — the deterministic path used by the suite.
  (Real Modbus TCP adds a socket round-trip per tag per tick and is correspondingly slower; it is
  exercised for *correctness* elsewhere, not for throughput here.)

## Baseline (reference run)
Measured on the developer machine (Windows 11, CPython 3.13, single core, in-process):

| Metric | Value |
|--------|-------|
| Parcels routed | **100 / 100** (A=50, B=50 — no drops, no mis-routes) |
| Wall-clock | **~1.7 s** |
| Simulated ticks | 870 (43.5 s of simulated time) |
| Tick rate | **~500 ticks/s** |
| Speed-up vs real time | **~25×** |
| Throughput | **~58 parcels/s** (wall-clock) |
| Determinism | identical results across repeated runs |

The advanced cell sorts this dense stream **100/100**; the MVP single-register cell would mis-route
it (see `tests/test_advanced_cell.py`). At 0.4 s spacing only ~4 parcels are in flight at once, well
within the 8-slot ring.

## Guard test
`tests/test_performance.py` (in the default suite) asserts:
- **`test_throughput_100_parcels_all_routed`** — exact 50/50 split, and wall-clock `< 15 s`
  (≈9× headroom over the baseline, so slow CI never flakes).
- **`test_run_is_deterministic`** — two runs of a 60-parcel stream produce identical results.

## Reproduce
```bash
python tests/test_performance.py        # prints the measured timing line
# or, with timing detail:
python -m pytest tests/test_performance.py -s -q
```

## Notes & limits
- The runner is intentionally single-threaded and synchronous (the PLC scan is driven manually) so
  ordering — and therefore the result — is deterministic; it is not optimised for raw speed.
- Throughput scales roughly linearly with parcel count at fixed `dt`; halving `dt` doubles ticks.
- These figures are a **baseline for regression spotting**, not a real-time-control guarantee.
