# Writing Scenarios

Scenarios are deterministic, timestamped event scripts in `scenarios/*.json`. They are
validated on load (`scenarios/schema.json` + `validate_scenario` in `scenario_runner.py`) and
run by `scripts/scenario_manager.py`.

## File shape
```json
{
  "name": "my_scenario",
  "description": "one line",
  "cell": "sorting_cell_mvp",
  "dt": 0.05,
  "duration": 6.0,
  "events": [ { "t": 0.0, "action": "press", "input": "input.start_pb" } ],
  "expect": { "sorted_a": 1, "sorted_b": 0, "jam_triggered": false }
}
```
| Field | Meaning |
|-------|---------|
| `dt` | fixed sim step in seconds (default 0.05). |
| `duration` | total sim seconds; runs `round(duration/dt)` ticks. |
| `events` | list of `{t, action, ...}`, applied at sim time `t` (sorted by `t`). |
| `expect` | optional asserted result fields; checked by `run-all`. |

## Actions
| action | extra fields | effect |
|--------|--------------|--------|
| `press` | `input` | set a button coil TRUE (reset also clears a stuck parcel) |
| `release` | `input` | set a button coil FALSE |
| `set_estop` | `value` (bool) | engage/release E-stop |
| `spawn_parcel` | `destination` (`CHUTE_A`/`CHUTE_B`), optional `id` | inject a parcel at the infeed |
| `inject_jam` | optional `id` | freeze a parcel (jam at pe_002) |
| `clear_jam` | — | remove stuck parcel(s) |

## Result fields you can assert in `expect`
`sorted_a`, `sorted_b`, `jam_triggered`, `jam_cleared`, `motor_on_ticks`, `ticks`,
`divert_on_ticks` (see `ScenarioRunner.run`).

## Cells (the `cell` field selects the runner profile)
- `sorting_cell_mvp` (default) — one shared `data.parcel_destination` latched at pe_002. Space
  parcels so only **one** is between the scan point (pe_001 @20 cm) and the diverter (90 cm) at a
  time — at 50 cm/s that is ≥ ~1.6 s apart.
- `sorting_cell_advanced` — per-parcel destinations via an 8-slot **FIFO ring** (ADR-0005), so
  densely-spaced parcels route correctly (e.g. `scenarios/dense_sort_advanced.json`: 8 parcels at
  0.4 s, ~3 in flight). The scenario manager picks the cell profile automatically from `cell`.

Geometry: speed 50 cm/s, parcel 10 cm, pe_001 @20, pe_002 @80, diverter @90, end @120
(see `simulation/scene_model.py`). A parcel reaches pe_002 ~1.6 s after spawn and routes ~1.8 s after.

## Validate & run
```bash
python scripts/scenario_manager.py validate scenarios/my_scenario.json
python scripts/scenario_manager.py run my_scenario --export-dir=telemetry/exports
```
A malformed scenario (unknown action, missing `input`, etc.) fails fast with a clear message.
