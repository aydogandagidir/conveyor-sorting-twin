# telemetry

SQLite-first event log with CSV/JSON export.

- `telemetry_logger.py` — `TelemetryLogger` (SQLite + export + typed helpers).
- `SCHEMA.md` — the `events` table and the event-type taxonomy (cycle / sort / fault /
  machine_state / …). The schema is **additive across phases** (new event types, no
  column changes), so old exports stay valid.
- `exports/` — generated CSV/JSON (gitignored).

## Usage
```python
from telemetry_logger import TelemetryLogger
tel = TelemetryLogger("telemetry/exports/run.db", scenario="my_run")
tel.log_machine_state("motor_run", detail="t=0.00")
tel.log_sort("CHUTE_A", 1, detail="count=1")
tel.log_fault("alarm.jam_001", True, detail="t=3.05")
tel.export_csv("telemetry/exports/run.csv")
tel.export_json("telemetry/exports/run.json")
tel.close()
```

## Export location
The scenario/demo runners default to `telemetry/exports/` and accept an override:
```bash
python scripts/run_scenario.py scenarios/barcode_sorting_basic.json --export-dir=/tmp/oltwin
python scripts/run_demo.py --export-dir=/tmp/oltwin
```
Useful for CI artifacts and containerized deployments.
