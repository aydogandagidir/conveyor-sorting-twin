# ADR-0005 — Multi-parcel destination tracking (FIFO ring)

- Status: Accepted — prototype proven (1.5f) and **rolled out** (Stage 2):
  `tags.sorting_cell_advanced.json` + cell-aware `ScenarioRunner`/`scenario_manager`
  (`dest_strategy="fifo_ring"`) + `scenarios/dense_sort_advanced.json` + `tests/test_advanced_cell.py`
  (advanced routes 8 dense parcels 4/4; the MVP single register mis-routes the same stream 2/6).
- Date: 2026-06-17
- Phase: 1.5 (Hardening — design & prototype)

## Context
The Phase 1 MVP cell carries a parcel's destination in a single shared holding
register `data.parcel_destination`, latched on the pe_002 rising edge. This assumes
**at most one parcel** between the barcode scan (pe_001) and the diverter (pe_002).
Real barcode scanners hit at irregular intervals; densely-spaced parcels make a later
parcel overwrite an earlier parcel's destination before it reaches pe_002 → silent
mis-routing. ADR-0003 flagged this; the Phase 1.5 analysis ranked it a top risk.

## Decision
Deliver destinations through a **FIFO ring of holding registers**
`data.dest_ring_0 .. data.dest_ring_{K-1}` (prototype `K = 8`):
- The plant **enqueues** a parcel's destination as it is scanned at pe_001
  (`ring[write_idx % K] = dest; write_idx++`).
- The PLC **dequeues** on the pe_002 rising edge
  (`dest = ring[read_idx % K]; read_idx++`) and routes/counts as before.

A **single-lane conveyor is strictly FIFO** (no overtaking), so the k-th parcel to
cross pe_001 is the k-th to cross pe_002 — dequeue order always matches enqueue order,
independent of how many parcels are buffered in the scan→divert zone.

## Options considered
- **A — ID-indexed ring (chosen):** small register ring + modulo indices. Bounded,
  simple, no per-parcel ID needed (FIFO order is implicit). K sized to the max parcels
  in flight between pe_001 and pe_002.
- **B — sliding window of N "next destination" registers:** equivalent capacity, more
  bookkeeping on the plant side. Rejected as no simpler than A.
- **C — per-parcel ID record (full tracking):** needed only if overtaking or out-of-order
  vision reads appear (multi-lane, merges). Deferred until such a cell exists.

## Scope of the improvement (important)
The ring fixes **destination delivery**, letting parcels pack as tight as ~parcel
length through the scan→divert buffer. It does **not** change the **diverter**
throughput limit: the single diverter still serialises parcels in the
pe_002→clear zone, so parcels must stay spaced enough that one clears before the next
reaches the decision point. These are independent limits.

## Prototype & verification
- `plc/control_logic_advanced.py` — FIFO-dequeue control program (same scan contract;
  plugs into `SoftPlc(control=...)`).
- `tests/test_multi_parcel_prototype.py` (through SceneModel ↔ gateway ↔ SoftPlc):
  - 12 densely-spaced parcels (0.4 s apart, ~3 in flight) all route correctly with the
    ring (counters 6/6).
  - The MVP single register mis-routes the same dense stream — proving the fix matters.

## Consequences / rollout (Phase 2)
- Promote the prototype to `protocol-gateway/config/tags.sorting_cell_advanced.json`
  and wire `scene_model`/`scenario_runner` to enqueue on scan events.
- Size `K` from the cell geometry (`ceil((pe2_x - pe1_x) / min_pitch) + margin`).
- Add overflow detection (`write_idx - read_idx > K`) → alarm; today the prototype
  assumes K is large enough.
- Phase 0/1 registries are untouched; this is an additive new cell variant.
