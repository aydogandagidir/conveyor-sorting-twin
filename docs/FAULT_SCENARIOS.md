# Fault & Control Scenario Library

The shipped deterministic scenarios (`scenarios/*.json`). Each carries an `expect` block
checked by `python scripts/scenario_manager.py run-all`.

| Scenario | Fault / control model | Expected outcome | Level |
|----------|-----------------------|------------------|-------|
| `barcode_sorting_basic` | none — 4 parcels A,B,A,B | sort A=2, B=2, no jam | intro |
| `stop_button_basic` | Stop pushbutton mid-run | motor halts; in-flight parcel never reaches diverter → A=0, B=0 | intro |
| `estop_during_run` | E-stop engaged then released + restart | motor stops then resumes; parcel completes → A=1 | intermediate |
| `jam_recovery_basic` | parcel jams at pe_002; reset after latch | `alarm.jam_001` latches, motor stops; reset clears; follow-up → B=1 | intermediate |
| `rapid_jam_reset` | jam + reset as soon as the alarm latches | jam triggered & cleared; follow-up → B=1 | intermediate |
| `dense_sort_advanced` | 8 parcels @ 0.4 s on the **advanced** (FIFO-ring) cell | all 8 route correctly → A=4, B=4 (the MVP cell would mis-route) | advanced |
| `back_to_back_sort` | 3 parcels A,B,A near the MVP min spacing (1.7 s) | each routed correctly → A=2, B=1 | intro |
| `motor_never_starts` | Start never pressed | motor stays off; nothing sorted (A=0, B=0) | intro |
| `two_jams` | two jam/reset cycles, then a clean sort | jam ×2 triggered & cleared; final → A=1 | intermediate |
| `estop_during_divert` | E-stop while a parcel is at the diverter | routing decision voided; parcel passes straight, uncounted (A=0, B=0) | advanced |

## Fault models in the simulator
- **Jam** — `inject_jam` freezes a parcel at pe_002; the PLC's 1 s dwell timer
  (`JAM_SCAN_LIMIT`) latches `alarm.jam_001` and stops the motor. `reset` clears it and the
  operator (scenario runner) removes the stuck parcel.
- **E-stop** — `set_estop true/false`. Engaged → motor + diverter de-energized immediately
  (safety). Releasing does **not** auto-restart; an explicit Start is required.
- **Stop** — momentary `input.stop_pb`; drops the running latch (distinct from E-stop).

## Run one / all
```bash
python scripts/scenario_manager.py run rapid_jam_reset
python scripts/scenario_manager.py run-all          # checks every expect block
python scripts/run_full_demo.py                     # + HTML/Markdown report
```

See `docs/SCENARIOS.md` to author new ones and `docs/TRAINER_GUIDE.md` for a teaching order.
