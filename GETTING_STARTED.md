# Getting started — a 5-minute tour

OpenLogiTwin is a deterministic digital twin of a conveyor **sorting cell** with a real PLC
control loop, real industrial protocols, and a browser **HMI** you can drive. This tour takes you
from clone to a running operator console, then through what you're looking at.

> No visual to look at yet? The live HMI is hosted here:
> **https://aydogandagidir.github.io/conveyor-sorting-twin/hmi/** (replay; zero install).

## Prerequisites
- **Python 3.9+** — the core has **no third-party dependencies** (stdlib only).
- *Optional:* Docker (for the turnkey container), and `pytest` / `pymodbus` / `asyncua` /
  `paho-mqtt` for the dev extras (`pip install -e ".[dev]"`).

## 1 · Run it
Pick whichever fits — all four land you at the same HMI.

```bash
git clone https://github.com/aydogandagidir/conveyor-sorting-twin.git
cd conveyor-sorting-twin

python -m openlogitwin                 # exports traces, serves the HMI + live twin, opens the browser
```
- **Console command:** `pip install -e .` then just `openlogitwin`.
- **Docker (turnkey):** `docker compose -f deployment/docker-compose.yml --profile demo up --build`
  → open <http://localhost:8099/hmi/>.
- **Zero install:** the hosted [GitHub Pages HMI](https://aydogandagidir.github.io/conveyor-sorting-twin/hmi/)
  (replay only — no live mode).

The launcher prints the URL (default <http://localhost:8099/hmi/>). Flags: `--no-live` (replay
only), `--no-browser`, `--host`, `--port`.

## 2 · Tour the HMI (replay)
The HMI opens in **REPLAY** mode, playing back a deterministic trace of the plant.

1. **Watch a sort.** Parcels ride the belt left→right; the diverter **DV-001** routes each to
   **Chute A** (up) or **Chute B** (down). The counts and the throughput KPI update live.
2. **Switch scenarios.** Use the scenario dropdown in the control bar — e.g. `jam_recovery_basic`
   to see a fault, or `dense_sort_advanced` for a dense stream.
3. **Scrub the timeline.** Pause / play and drag the seek slider; the embedded trend tracks
   sorted A vs B.
4. **Click equipment.** Click the motor, the diverter, or a chute to open its **faceplate**
   (state, mode, interlocks). An alarm row opens a faceplate with its ISA-18.2 **rationalisation**
   (probable cause / consequence / corrective action).
5. **Change the view level.** The **L1 · Line / L2 · Cell / L3 · I/O** chips switch between a line
   overview, the cell mimic, and a live I/O tag table.
6. **Toggle the theme.** The **◐ Theme** button switches the light / dark (control-room) palette.

## 3 · Go live (drive the real twin)
If you launched with live mode (the default), click **● Go live** — the HMI connects to the
running twin over a WebSocket and switches to **LIVE**.

1. **Start** — the real soft-PLC runs the motor; parcels start sorting (Chute A/B counts climb).
2. **Inject jam** — a parcel sticks at PE-002; after the ~1 s jam timer the motor stops and a
   **priority-1 alarm** appears (docked banner blinks until acknowledged; a redundant indicator
   shows at the diverter — the belt is never recoloured).
3. **Reset** — clears the jam; the cell restarts.
4. **E-STOP** — latches the cell de-energised (a P1 alarm) until you Reset.
5. **Stop live** — returns to REPLAY.

These buttons drive the **actual control logic** — the same soft-PLC the test suite verifies.

## 4 · What you're looking at
The HMI follows the **High-Performance HMI** doctrine (ANSI/ISA-101; alarms per ANSI/ISA-18.2):
gray canvas, equipment drawn as low-contrast outlines, **colour reserved for live data and
alarms**, status shown by **brightness + a word** (never red/green lamps), no gradients or 3-D.
It reads calm on purpose — the one red element on the screen means something needs attention.

## 5 · Under the hood
- **`simulation/scene_model.py`** — a deterministic, fixed-step plant (the test oracle).
- **`plc/control_logic_mvp.py`** on a soft-PLC — routing, counting, the jam timer, E-stop fail-safe.
- **Real Modbus TCP** (hand-rolled, stdlib) carries the I/O; OPC UA and MQTT are also wired.
- The HMI is a **view** over that same plant — replay traces are exported from it, and live mode
  streams it. Nothing in the HMI is a hand-built mock.

## 6 · Next steps
```bash
python -m openlogitwin test            # run the full suite (stdlib only) → SUITE GREEN
python -m openlogitwin demo            # run every scenario → telemetry/exports/demo_report.html
python -m openlogitwin scenarios       # list / validate / run scenarios
```
- **Author a scenario** — see [`docs/SCENARIOS.md`](docs/SCENARIOS.md) and [`docs/FAULT_SCENARIOS.md`](docs/FAULT_SCENARIOS.md).
- **Drive it from a real stack** — FUXA / OpenPLC / Godot: [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md), [`hmi/fuxa/INTEGRATION.md`](hmi/fuxa/INTEGRATION.md).
- **Why it's built this way** — the decision records in [`adr/`](adr) (incl. ADR-0009, the live-HMI WebSocket).
- **Where it's going** — [`docs/ROADMAP.md`](docs/ROADMAP.md).
