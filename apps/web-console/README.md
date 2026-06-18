# web-console — placeholder (Phase 2+)

Not implemented yet. A web console (operator/monitoring UI) is **out of scope for
Phase 0** per the project rules ("Do not overbuild UI before proving the
PLC-simulation round-trip").

Phase 0 proves the loop headlessly via:
- `tests/verify_phase0.py`
- `scripts/run_demo.py`

When built (Phase 2+), this app will consume the same tag registry and telemetry
that already exist. No code here yet by design.
