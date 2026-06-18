# Trainer Guide

OpenLogiTwin as a hands-on PLC commissioning lab: a deterministic conveyor sorting cell
driven over real Modbus TCP, with fault injection and a results report.

## Prerequisites
- Python 3.9+ (no third-party packages for the core).
- Optional: Docker + FUXA for the HMI (`docs/DEPLOYMENT.md`); OpenPLC Runtime v4 to replace
  the soft-PLC with a real PLC (`plc/examples/`).

## Suggested progression
Run each with `python scripts/scenario_manager.py run <name>`; learners read the printed
result and the telemetry export.

1. **`barcode_sorting_basic`** — *Understand the sense→decide→act loop.* A photo-eye (pe_002)
   triggers a routing decision from the barcode word; the diverter sends parcels to A or B.
2. **`stop_button_basic`** — *Latching vs momentary.* A momentary Stop drops the run latch;
   the line halts and the in-flight parcel is not sorted.
3. **`estop_during_run`** — *Safety override & recovery.* E-stop stops everything; releasing it
   does not auto-start — the operator must press Start again.
4. **`jam_recovery_basic`** — *Fault detection & acknowledge.* A stuck parcel keeps pe_002
   blocked; the 1 s dwell timer latches the jam alarm and stops the motor; Reset clears it.
5. **`rapid_jam_reset`** — *Timing of detection.* Same fault, reset the moment the alarm latches.

## Hands-on exercise — tune the jam timer
1. Open `plc/control_logic_mvp.py`; change `JAM_SCAN_LIMIT` from `20` to `10`.
2. Re-run `python scripts/scenario_manager.py run jam_recovery_basic`.
3. Observe the jam latches sooner (~0.5 s instead of ~1.0 s at dt=0.05 s). Discuss the
   trade-off: faster detection vs false trips on a slow/heavy parcel. Restore `20` after.
> Note: the soft-PLC scans once per simulation tick (`dt`, default 0.05 s). On a **real**
> OpenPLC the jam timer is a `TON` in **seconds** (`T#1s`, see `plc/examples/02_sorting_cell_mvp.st`),
> so it is independent of scan rate — explain why seconds are safer than scan counts.

## Reading results
- Per-run telemetry: `telemetry/exports/<scenario>.json` / `.csv` (event taxonomy in
  `telemetry/SCHEMA.md`).
- Aggregate demo report: `python scripts/run_full_demo.py` →
  `telemetry/exports/demo_report.html` (throughput, sort distribution, fault events).

## Going further
- Author your own scenario: `docs/SCENARIOS.md`.
- Replace the soft-PLC with real OpenPLC: `plc/examples/README.md`.
- Dense parcel streams need per-parcel destination tracking (`control_logic_advanced.py`,
  ADR-0005); the default cell assumes parcels are spaced (sparse load).
