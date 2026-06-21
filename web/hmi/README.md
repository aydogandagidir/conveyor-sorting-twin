# Web HMI — live sorting-cell visualization

A zero-install, browser-based HMI that **replays deterministic simulation traces** of the
sorting cell: parcels move along the conveyor, route at the diverter, and the chute counters,
status lamps, and event log update live. It is a *view* over the same plant the test suite
verifies (`simulation/scene_model.py`) — the trace is exported from a real scenario run, so the
animation shows real sim data, not a hand-built mock.

## Run it
The HMI fetches its data from `traces/*.json`, so it must be served over HTTP (browsers block
`fetch` from `file://`):

```bash
python scripts/export_trace.py        # writes web/hmi/traces/*.json + index.json
python -m http.server --directory web 8099
# open http://localhost:8099/hmi/
```

On GitHub Pages it is published automatically at `/<repo>/hmi/` (the `pages` workflow runs
`export_trace.py` and copies `web/hmi/` into the site).

## How it works
- `scripts/export_trace.py` runs a scenario through the cell-aware `ScenarioRunner` with
  `record_trace=True` and writes a per-tick frame stream (parcel positions + destination,
  motor/diverter/jam, counters, `pe_001`/`pe_002`) plus the cell layout.
- `index.html` loads a trace, maps cm → pixels, and interpolates between frames for smooth
  motion. It is **`setInterval`-driven** (not only `requestAnimationFrame`) so it keeps running
  in background/kiosk tabs. Controls: scenario picker, play/pause, speed, and a timeline scrubber.

`scene_model.py` stays the deterministic test oracle; this is the visualization layer.
Structural wiring is guarded by `tests/test_web_hmi.py`.
