# Telemetry Schema

SQLite-first event log. One row per event. Exported to CSV/JSON unchanged.

## Table `events`
| Column       | Type    | Meaning |
|--------------|---------|---------|
| `id`         | INTEGER | Auto-increment primary key (event order). |
| `ts_iso`     | TEXT    | UTC ISO-8601 timestamp. |
| `ts_unix`    | REAL    | UTC Unix timestamp. |
| `scenario`   | TEXT    | Scenario / cell name (e.g. `barcode_sorting_basic`). |
| `event_type` | TEXT    | Event category (taxonomy below). |
| `tag`        | TEXT    | Subject of the event (tag name, chute, state, …). |
| `value`      | TEXT    | Event value (stringified). |
| `detail`     | TEXT    | Free-form detail (often `t=<sim seconds>`). |

The schema is **additive across phases**: Phase 1 introduced new `event_type`
values only — no column changes — so Phase 0 exports remain valid.

## Event taxonomy (Phase 1)
| `event_type`    | Emitted by | `tag` | `value` | Meaning |
|-----------------|------------|-------|---------|---------|
| `cycle`         | `log_cycle` | phase, e.g. `parcel_spawn` | — | Cell/parcel cycle event |
| `sort`          | `log_sort`  | `CHUTE_A`/`CHUTE_B` | destination id | A parcel was sorted to a chute |
| `fault`         | `log_fault` | alarm tag, e.g. `alarm.jam_001` | `True`/`False` | Fault asserted / cleared |
| `machine_state` | `log_machine_state` | `motor_run`/`motor_stop` | — | Machine state transition |
| `jam_inject`    | scenario runner | `scene` | — | Scenario injected a jam (test stimulus) |

Phase 0 also uses: `tag_change`, `estop`, `parcel_present`, `parcel_cleared`,
`sorted`.

## Helper API (`telemetry/telemetry_logger.py`)
```python
tel.log_event(event_type, tag=None, value=None, detail=None)  # generic
tel.log_cycle(phase, detail=None)
tel.log_sort(chute, destination, detail=None)
tel.log_fault(name, active, detail=None)
tel.log_machine_state(state, detail=None)
tel.export_csv(path); tel.export_json(path)
```

## Example (jam_recovery_basic)
```
machine_state motor_run    t=0.00
cycle         parcel_spawn P1 dest=CHUTE_A
jam_inject    scene        parcel=P1
machine_state motor_stop   t=3.05
fault         alarm.jam_001 True   t=3.05
fault         alarm.jam_001 False  cleared t=4.00
machine_state motor_run    t=4.50
cycle         parcel_spawn P2 dest=CHUTE_B
sort          CHUTE_B      count=1 t=6.60
```
