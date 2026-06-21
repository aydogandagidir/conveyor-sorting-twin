# Web HMI — high-performance (ISA-101) sorting-cell HMI

A zero-install, browser-based operator HMI that **replays deterministic simulation traces** of the
sorting cell. It is a *view* over the same plant the test suite verifies (`simulation/scene_model.py`),
fed by exported traces — real sim data, not a hand-built mock.

The visual design follows the **High-Performance HMI** doctrine (ANSI/ISA-101, alarm UX per
ANSI/ISA-18.2), per Bill Hollifield / PAS and Rockwell's Process HMI Style Guide (PROCES-WP023).

## Design principles applied
- **Gray canvas, equipment by outline.** Background is light gray (`#E0E0E0`); equipment is drawn
  as low-contrast 2-D shapes filled the same colour as the canvas, so it reads by outline.
- **Colour only for live data and alarms.** Live numeric values use one strategic dark colour
  (`#1F4E79`); the small alarm set (P1 `#C0392B` / P2 `#E67E22` / P3) is used for nothing else.
- **Status by brightness + word, never red/green lamps.** A running motor is shown *brighter than
  the background* plus a `RUN`/`STOP` word — the red-off/green-on paradigm is the worst HP-HMI
  violation (and colour-blind-unsafe).
- **No gradients, drop shadows, glow, 3-D, or decorative animation** (the "make it prettier / like a
  phone app" anti-patterns that read as amateurish). Numerics use tabular figures.
- **ISA-18.2 alarms.** A docked banner shows the highest-priority unacknowledged alarm; an alarm
  summary table lists priority (icon + colour + label), time, tag, description and state
  (`UNACK`/`ACK`/`RTN`); unacknowledged rows/banner blink until acknowledged. A jam is surfaced by a
  redundantly-coded indicator *next to* the diverter — the belt is never recoloured.
- **Situational awareness.** Persistent status bar, level breadcrumb, analog deviation indicators
  (value vs a light-blue normal band), and an embedded sorted-parcels trend.

## Structure
- `index.html` — semantic markup (status bar, alarm banner, breadcrumb, mimic, KPI rail, trend,
  alarm summary, control bar).
- `hmi.css` — the HP-HMI design system: palette tokens (light default + a `[data-theme="dark"]`
  control-room variant), components, no gradients/shadows.
- `hmi.js` — the replay engine (trace interpolation, `setInterval` tick so it runs in background/kiosk
  tabs) and the HP-HMI render + alarm model.

## Run it
The HMI fetches `traces/*.json`, so serve it over HTTP (browsers block `fetch` from `file://`):
```bash
python scripts/export_trace.py        # writes web/hmi/traces/*.json + index.json
python -m http.server --directory web 8099
# open http://localhost:8099/hmi/
```
On GitHub Pages it is published at `/<repo>/hmi/` (the `pages` workflow runs `export_trace.py` and
copies `web/hmi/`). `scene_model.py` stays the deterministic test oracle; structural + HP-HMI-compliance
wiring is guarded by `tests/test_web_hmi.py`.
